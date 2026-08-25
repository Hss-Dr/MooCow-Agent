#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import re
import time
import os
import json

import copy
from elasticsearch import Elasticsearch
from elasticsearch_dsl import UpdateByQuery, Q, Search, Index
from service.core.rag.utils import singleton
from service.core.api.utils.file_utils import get_project_base_directory
from service.core.rag.utils.doc_store_conn import MatchExpr, OrderByExpr, MatchTextExpr, MatchDenseExpr, FusionExpr
from service.core.rag.nlp import is_english
from dotenv import load_dotenv

load_dotenv()

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ATTEMPT_TIME = 2
PAGERANK_FLD = "pagerank_fea"
TAG_FLD = "tag_feas"

logger = logging.getLogger('ragflow.es_conn')


@singleton
class ESConnection():
    def __init__(self):
        self.info = {}
        logger.info(f"Connecting to Elasticsearch at {ES_HOST}")
        # ES密码从环境变量读取,与docker-compose.yml中gsk-es-01容器的ELASTIC_PASSWORD一致
        ES_PASSWORD = os.getenv("ELASTIC_PASSWORD", "elastic123456")
        self.es = Elasticsearch(
            [ES_HOST],  # Elasticsearch URL
            basic_auth=("elastic", ES_PASSWORD),  # 用户名和密码
            verify_certs=False,  # 禁用 SSL 证书验证
            timeout=600
        )
        logger.info("Elasticsearch connection established")

        fp_mapping = os.path.join(get_project_base_directory(), "conf", "mapping.json")
        self.mapping = json.load(open(fp_mapping, "r"))


    """
    Helper functions for search result
    """

    def getTotal(self, res):
        if isinstance(res["hits"]["total"], type({})):
            return res["hits"]["total"]["value"]
        return res["hits"]["total"]

    def getChunkIds(self, res):
        return [d["_id"] for d in res["hits"]["hits"]]
    

    def getHighlight(self, res, keywords: list[str], fieldnm: str):
        ans = {}
        for d in res["hits"]["hits"]:
            hlts = d.get("highlight")
            if not hlts:
                continue
            txt = "...".join([a for a in list(hlts.items())[0][1]])
            if not is_english(txt.split()):
                ans[d["_id"]] = txt
                continue

            txt = d["_source"][fieldnm]
            txt = re.sub(r"[\r\n]", " ", txt, flags=re.IGNORECASE | re.MULTILINE)
            txts = []
            for t in re.split(r"[.?!;\n]", txt):
                for w in keywords:
                    t = re.sub(r"(^|[ .?/'\"\(\)!,:;-])(%s)([ .?/'\"\(\)!,:;-])" % re.escape(w), r"\1<em>\2</em>\3", t,
                               flags=re.IGNORECASE | re.MULTILINE)
                if not re.search(r"<em>[^<>]+</em>", t, flags=re.IGNORECASE | re.MULTILINE):
                    continue
                txts.append(t)
            ans[d["_id"]] = "...".join(txts) if txts else "...".join([a for a in list(hlts.items())[0][1]])

        return ans
    

    def getAggregation(self, res, fieldnm: str):
        agg_field = "aggs_" + fieldnm
        if "aggregations" not in res or agg_field not in res["aggregations"]:
            return list()
        bkts = res["aggregations"][agg_field]["buckets"]
        return [(b["key"], b["doc_count"]) for b in bkts]

    def getFields(self, res, fields: list[str]) -> dict[str, dict]:
        res_fields = {}
        if not fields:
            return {}
        for d in self.__getSource(res):
            m = {n: d.get(n) for n in fields if d.get(n) is not None}
            for n, v in m.items():
                if isinstance(v, list):
                    m[n] = v
                    continue
                if not isinstance(v, str):
                    m[n] = str(m[n])
                # if n.find("tks") > 0:
                #     m[n] = rmSpace(m[n])

            if m:
                res_fields[d["id"]] = m
        return res_fields


    def __getSource(self, res):
        rr = []
        for d in res["hits"]["hits"]:
            d["_source"]["id"] = d["_id"]
            d["_source"]["_score"] = d["_score"]
            rr.append(d["_source"])
        return rr

    """
    Database operations
    """
    def _ensure_index(self, indexName: str):
        """
        确保索引存在,且按 conf/mapping.json 创建(含 dynamic_templates:*_1024_vec → dense_vector)。
        必须在写入前调用:否则 es.bulk 自动创建的索引会走默认动态映射,
        q_1024_vec 会被推断成普通 float 数组而非 dense_vector,导致向量检索失效。
        """
        try:
            if self.es.indices.exists(index=indexName):
                return
            self.es.indices.create(
                index=indexName,
                settings=self.mapping.get("settings"),
                mappings=self.mapping.get("mappings"),
            )
            logger.info(f"ESConnection: created index '{indexName}' with mapping.json")
        except Exception as e:
            # 并发下可能已被其它请求创建,忽略 already-exists;其余异常继续抛出
            if "resource_already_exists_exception" in str(e):
                return
            raise

    def insert(self, documents: list[dict], indexName: str, knowledgebaseId: str = None) -> list[str]:
        # Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-bulk.html
        self._ensure_index(indexName)
        operations = []
        for d in documents:
            assert "_id" not in d
            assert "id" in d
            d_copy = copy.deepcopy(d)
            meta_id = d_copy.pop("id", "")
            operations.append(
                {"index": {"_index": indexName, "_id": meta_id}})
            operations.append(d_copy)

        res = []
        for _ in range(ATTEMPT_TIME):
            try:
                res = []
                r = self.es.bulk(index=(indexName), operations=operations,
                                 refresh=False, timeout="60s")
                if re.search(r"False", str(r["errors"]), re.IGNORECASE):
                    return res

                for item in r["items"]:
                    for action in ["create", "delete", "index", "update"]:
                        if action in item and "error" in item[action]:
                            res.append(str(item[action]["_id"]) + ":" + str(item[action]["error"]))
                return res
            except Exception as e:
                res.append(str(e))
                logger.warning("ESConnection.insert got exception: " + str(e))
                res = []
                if re.search(r"(Timeout|time out)", str(e), re.IGNORECASE):
                    res.append(str(e))
                    time.sleep(3)
                    continue
        return res
    

    def search(
            self, selectFields: list[str],
            highlightFields: list[str],
            condition: dict,
            matchExprs: list[MatchExpr],
            orderBy: OrderByExpr,
            offset: int,
            limit: int,
            indexNames: str | list[str],
            knowledgebaseIds: list[str],
            aggFields: list[str] = [],
            rank_feature: dict | None = None,
            use_rrf: bool = True,
            rrf_k: int = 60,
    ):
        """
        Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html

        粗排融合模式:
        - use_rrf=True(默认,新逻辑):当 matchExprs 同时包含 BM25 与 KNN 两路时,拆成
          两次纯 ES 查询,在客户端做 RRF(Reciprocal Rank Fusion,score = Σ 1/(k+rank))。
          k=60 是 Cormack 2009 论文推荐值。ES 8.11.3 basic license 无原生 rrf 检索器,
          故走客户端实现;详见 _search_rrf()。
        - use_rrf=False 或缺一路:回退到原有 weighted_sum(0.05,0.95),一次 ES 查询。
        """
        if isinstance(indexNames, str):
            indexNames = indexNames.split(",")
        assert isinstance(indexNames, list) and len(indexNames) > 0
        assert "_id" not in condition

        # 触发 RRF:显式启用 + 两路都在(BM25 + KNN)
        has_text = any(isinstance(m, MatchTextExpr) for m in matchExprs)
        has_dense = any(isinstance(m, MatchDenseExpr) for m in matchExprs)
        if use_rrf and has_text and has_dense:
            return self._search_rrf(
                selectFields, highlightFields, condition, matchExprs,
                orderBy, offset, limit, indexNames, knowledgebaseIds,
                aggFields, rank_feature, k=rrf_k,
            )

        bqry = Q("bool", must=[])
        condition["kb_id"] = knowledgebaseIds
        for k, v in condition.items():
            if k == "available_int":
                if v == 0:
                    bqry.filter.append(Q("range", available_int={"lt": 1}))
                else:
                    bqry.filter.append(
                        Q("bool", must_not=Q("range", available_int={"lt": 1})))
                continue
            if not v:
                continue
            if isinstance(v, list):
                bqry.filter.append(Q("terms", **{k: v}))
            elif isinstance(v, str) or isinstance(v, int):
                bqry.filter.append(Q("term", **{k: v}))
            else:
                raise Exception(
                    f"Condition `{str(k)}={str(v)}` value type is {str(type(v))}, expected to be int, str or list.")

        s = Search()
        vector_similarity_weight = 0.5
        for m in matchExprs:
            if isinstance(m, FusionExpr) and m.method == "weighted_sum" and "weights" in m.fusion_params:
                assert len(matchExprs) == 3 and isinstance(matchExprs[0], MatchTextExpr) and isinstance(matchExprs[1],
                                                                                                        MatchDenseExpr) and isinstance(
                    matchExprs[2], FusionExpr)
                weights = m.fusion_params["weights"]
                vector_similarity_weight = float(weights.split(",")[1])
        for m in matchExprs:
            if isinstance(m, MatchTextExpr):
                minimum_should_match = m.extra_options.get("minimum_should_match", 0.0)
                if isinstance(minimum_should_match, float):
                    minimum_should_match = str(int(minimum_should_match * 100)) + "%"
                bqry.must.append(Q("query_string", fields=m.fields,
                                   type="best_fields", query=m.matching_text,
                                   minimum_should_match=minimum_should_match,
                                   boost=1))
                bqry.boost = 1.0 - vector_similarity_weight

            elif isinstance(m, MatchDenseExpr):
                assert (bqry is not None)
                similarity = 0.0
                if "similarity" in m.extra_options:
                    similarity = m.extra_options["similarity"]
                s = s.knn(m.vector_column_name,
                          m.topn,
                          m.topn * 2,
                          query_vector=list(m.embedding_data),
                          filter=bqry.to_dict(),
                          similarity=similarity,
                          )

        if bqry and rank_feature:
            for fld, sc in rank_feature.items():
                if fld != PAGERANK_FLD:
                    fld = f"{TAG_FLD}.{fld}"
                bqry.should.append(Q("rank_feature", field=fld, linear={}, boost=sc))

        if bqry:
            s = s.query(bqry)
        for field in highlightFields:
            s = s.highlight(field)

        if orderBy:
            orders = list()
            for field, order in orderBy.fields:
                order = "asc" if order == 0 else "desc"
                if field in ["page_num_int", "top_int"]:
                    order_info = {"order": order, "unmapped_type": "float",
                                  "mode": "avg", "numeric_type": "double"}
                elif field.endswith("_int") or field.endswith("_flt"):
                    order_info = {"order": order, "unmapped_type": "float"}
                else:
                    order_info = {"order": order, "unmapped_type": "text"}
                orders.append({field: order_info})
            s = s.sort(*orders)

        for fld in aggFields:
            s.aggs.bucket(f'aggs_{fld}', 'terms', field=fld, size=1000000)

        if limit > 0:
            s = s[offset:offset + limit]
        q = s.to_dict()
        logger.debug(f"ESConnection.search {str(indexNames)} query: " + json.dumps(q))

        for i in range(ATTEMPT_TIME):
            try:
                #print(json.dumps(q, ensure_ascii=False))
                res = self.es.search(index=indexNames,
                                     body=q,
                                     timeout="600s",
                                     # search_type="dfs_query_then_fetch",
                                     track_total_hits=True,
                                     _source=True,
                                     ignore_unavailable=True,
                                     allow_no_indices=True)
                if str(res.get("timed_out", "")).lower() == "true":
                    raise Exception("Es Timeout.")
                logger.debug(f"ESConnection.search {str(indexNames)} res: " + str(res))
                return res
            except Exception as e:
                logger.exception(f"ESConnection.search {str(indexNames)} query: " + str(q))
                if str(e).find("Timeout") > 0:
                    continue
                raise e
        logger.error("ESConnection.search timeout for 3 times!")
        raise Exception("ESConnection.search timeout.")

    def _search_rrf(
            self, selectFields: list[str],
            highlightFields: list[str],
            condition: dict,
            matchExprs: list[MatchExpr],
            orderBy: OrderByExpr,
            offset: int,
            limit: int,
            indexNames: list[str],
            knowledgebaseIds: list[str],
            aggFields: list[str] = [],
            rank_feature: dict | None = None,
            k: int = 60,
            topk_per_route: int | None = None,
    ):
        """
        客户端 RRF (Reciprocal Rank Fusion) 融合两路检索:
          - 路 1: 纯 BM25(query_string + kb_id/available_int 过滤 + rank_feature)
          - 路 2: 纯 KNN(dense vector + 同一 filter)
        融合公式: score(id) = Σ 1/(k + rank_i),k=60(Cormack 2009 论文推荐值)。

        与原 search() 返回结构对齐(hits.hits + aggregations),上层 getChunkIds/
        getFields/getHighlight/getAggregation/getTotal 无感知。
        """
        # 每路取多少候选;至少 128,或页面窗口末尾,取大者。
        # 融合池够大才有意义(单路少了会导致 tail 没被融合到)。
        if topk_per_route is None:
            topk_per_route = max(offset + limit, 128)

        # ---- 1. 构造 filter(两路共用) ----
        filter_bqry = Q("bool")
        cond = dict(condition)
        cond["kb_id"] = knowledgebaseIds
        for kf, vf in cond.items():
            if kf == "available_int":
                if vf == 0:
                    filter_bqry.filter.append(Q("range", available_int={"lt": 1}))
                else:
                    filter_bqry.filter.append(
                        Q("bool", must_not=Q("range", available_int={"lt": 1})))
                continue
            if not vf:
                continue
            if isinstance(vf, list):
                filter_bqry.filter.append(Q("terms", **{kf: vf}))
            elif isinstance(vf, (str, int)):
                filter_bqry.filter.append(Q("term", **{kf: vf}))
            else:
                raise Exception(
                    f"Condition `{kf}={vf}` type is {type(vf)}, expected int/str/list.")

        match_text = next((m for m in matchExprs if isinstance(m, MatchTextExpr)), None)
        match_dense = next((m for m in matchExprs if isinstance(m, MatchDenseExpr)), None)

        # ---- 2. 路 1: 纯 BM25(带 filter + rank_feature) ----
        bm25_bqry = Q("bool", filter=list(filter_bqry.filter))
        if match_text is not None:
            minimum_should_match = match_text.extra_options.get("minimum_should_match", 0.0)
            if isinstance(minimum_should_match, float):
                minimum_should_match = str(int(minimum_should_match * 100)) + "%"
            bm25_bqry.must.append(Q(
                "query_string", fields=match_text.fields,
                type="best_fields", query=match_text.matching_text,
                minimum_should_match=minimum_should_match, boost=1,
            ))
        # rank_feature (pagerank/tag_fea) 只影响词项相关性,不作用于 KNN
        if rank_feature:
            for fld, sc in rank_feature.items():
                fld_name = fld if fld == PAGERANK_FLD else f"{TAG_FLD}.{fld}"
                bm25_bqry.should.append(Q("rank_feature", field=fld_name, linear={}, boost=sc))

        bm25_search = Search().query(bm25_bqry)
        for field in highlightFields:
            bm25_search = bm25_search.highlight(field)
        # 聚合只在 BM25 路做一次(与原 search 保持一致的返回口径)
        for fld in aggFields:
            bm25_search.aggs.bucket(f'aggs_{fld}', 'terms', field=fld, size=1000000)
        if orderBy and getattr(orderBy, "fields", None):
            orders = []
            for field, order in orderBy.fields:
                order = "asc" if order == 0 else "desc"
                if field in ["page_num_int", "top_int"]:
                    order_info = {"order": order, "unmapped_type": "float",
                                  "mode": "avg", "numeric_type": "double"}
                elif field.endswith("_int") or field.endswith("_flt"):
                    order_info = {"order": order, "unmapped_type": "float"}
                else:
                    order_info = {"order": order, "unmapped_type": "text"}
                orders.append({field: order_info})
            bm25_search = bm25_search.sort(*orders)
        bm25_search = bm25_search[0:topk_per_route]
        bm25_body = bm25_search.to_dict()

        bm25_res = None
        bm25_ids: list[str] = []
        highlight_map: dict[str, dict] = {}
        aggregations: dict | None = None
        try:
            bm25_res = self.es.search(
                index=indexNames, body=bm25_body,
                timeout="600s", track_total_hits=True, _source=True,
                ignore_unavailable=True, allow_no_indices=True,
            )
            bm25_ids = [hit["_id"] for hit in bm25_res["hits"]["hits"]]
            if "aggregations" in bm25_res:
                aggregations = bm25_res["aggregations"]
            for hit in bm25_res["hits"]["hits"]:
                if "highlight" in hit:
                    highlight_map[hit["_id"]] = hit["highlight"]
        except Exception as e:
            logger.warning(f"ESConnection._search_rrf BM25 route failed: {e}")

        # ---- 3. 路 2: 纯 KNN(带同一 filter,不带 rank_feature) ----
        knn_res = None
        knn_ids: list[str] = []
        if match_dense is not None:
            knn_body = {
                "field": match_dense.vector_column_name,
                "query_vector": list(match_dense.embedding_data),
                "k": min(match_dense.topn, topk_per_route),
                "num_candidates": max(match_dense.topn * 2, topk_per_route * 2),
                "filter": filter_bqry.to_dict(),
            }
            similarity = match_dense.extra_options.get("similarity", 0.0)
            if similarity:
                knn_body["similarity"] = similarity
            try:
                knn_res = self.es.search(
                    index=indexNames, knn=knn_body, size=topk_per_route,
                    timeout="600s", track_total_hits=True, _source=True,
                    ignore_unavailable=True, allow_no_indices=True,
                )
                knn_ids = [hit["_id"] for hit in knn_res["hits"]["hits"]]
            except Exception as e:
                logger.warning(f"ESConnection._search_rrf KNN route failed: {e}")

        # ---- 4. RRF 融合 ----
        rrf_scores: dict[str, float] = {}
        for rank, doc_id in enumerate(bm25_ids, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        for rank, doc_id in enumerate(knn_ids, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)

        fused_ids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])
        total_fused = len(fused_ids)
        page_ids = fused_ids[offset:offset + limit] if limit > 0 else fused_ids

        # ---- 5. id → _index 映射(mget 需要,混合库场景一个 id 只属于一个索引) ----
        id_to_index: dict[str, str] = {}
        if bm25_res:
            for hit in bm25_res["hits"]["hits"]:
                id_to_index[hit["_id"]] = hit["_index"]
        if knn_res:
            for hit in knn_res["hits"]["hits"]:
                id_to_index.setdefault(hit["_id"], hit["_index"])

        # ---- 6. mget 拉取完整文档字段(vector/content_ltks 等,精排要用) ----
        # selectFields 若上层给了则做 _source 过滤(节省带宽,注意必须包含 q_XXX_vec)
        source_spec = selectFields if selectFields else True
        hits = []
        if page_ids:
            try:
                mget_docs_spec = [
                    {"_index": id_to_index.get(_id, indexNames[0]),
                     "_id": _id, "_source": source_spec}
                    for _id in page_ids
                ]
                mget_res = self.es.mget(body={"docs": mget_docs_spec})
                for doc in mget_res["docs"]:
                    if not doc.get("found"):
                        continue
                    hit = {
                        "_index": doc["_index"],
                        "_id": doc["_id"],
                        "_score": rrf_scores[doc["_id"]],
                        "_source": doc.get("_source", {}),
                    }
                    if doc["_id"] in highlight_map:
                        hit["highlight"] = highlight_map[doc["_id"]]
                    hits.append(hit)
            except Exception as e:
                logger.exception(f"ESConnection._search_rrf mget failed: {e}")

        return {
            "hits": {
                "total": {"value": total_fused, "relation": "eq"},
                "hits": hits,
            },
            "aggregations": aggregations or {},
            "timed_out": False,
        }

    def delete(self, condition: dict, indexName: str, knowledgebaseId: str) -> int:
        """
        删除符合条件的文档
        
        Args:
            condition: 删除条件
            indexName: 索引名称
            knowledgebaseId: 知识库ID
            
        Returns:
            删除的文档数量
        """
        try:
            # 构建删除查询
            query = {
                "query": {
                    "bool": {
                        "must": []
                    }
                }
            }
            
            # 添加知识库ID条件
            if knowledgebaseId:
                query["query"]["bool"]["must"].append({"term": {"kb_id": knowledgebaseId}})
            
            # 添加其他条件
            for field, value in condition.items():
                if isinstance(value, list):
                    query["query"]["bool"]["must"].append({"terms": {field: value}})
                elif isinstance(value, str) and value.startswith("*") and value.endswith("*"):
                    # 通配符查询（两端都有*）
                    query["query"]["bool"]["must"].append({"wildcard": {field: value}})
                elif isinstance(value, str) and (value.startswith("*") or value.endswith("*")):
                    # 通配符查询（一端有*）
                    query["query"]["bool"]["must"].append({"wildcard": {field: value}})
                else:
                    # 精确匹配
                    query["query"]["bool"]["must"].append({"term": {field: value}})
            
            # 打印调试信息
            print(f"ES 删除查询: {json.dumps(query, ensure_ascii=False, indent=2)}")
            print(f"索引名: {indexName}")
            
            # 执行删除
            response = self.es.delete_by_query(
                index=indexName,
                body=query,
                refresh=True
            )
            
            print(f"ES 删除响应: {response}")
            
            return response["deleted"]
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {str(e)}")
            print(f"ES 删除失败: {str(e)}")
            return 0
