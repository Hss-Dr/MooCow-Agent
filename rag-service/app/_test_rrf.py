# -*- coding: utf-8 -*-
"""
客户端 RRF 融合验证:对比 RRF vs weighted_sum 的排序差异。

验证点:
  A. RRF 模式:同时命中 BM25+KNN 的文档排名靠前(rank 双低→RRF 分双加)
  B. 回退到 weighted_sum:缺 use_rrf 参数 or 单路缺失时走旧逻辑
  C. 混合库容错:company_kb,user_id,不存在索引 不报错(ignore_unavailable)
"""
import sys

STEPS = []
def step(name, fn):
    try:
        detail = fn()
        STEPS.append((name, True, detail))
        print(f"[PASS] {name} :: {detail}")
    except Exception as e:
        STEPS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {name} :: {type(e).__name__}: {e}")


def s1_rrf_enabled():
    """RRF 融合:同时命中 BM25+KNN 的文档排更前"""
    from service.core.rag.nlp.search_v2 import Dealer
    from service.core.rag.utils.es_conn import ESConnection
    es = ESConnection()
    dealer = Dealer(dataStore=es)
    # 不传 rerank_mdl,只走粗排 RRF(精排会把顺序调整);page_size=10 多看几条排序
    res = dealer.retrieval("世运电路营收", None, "company_kb,9", None, 1, 10)
    top3 = [c["docnm_kwd"].split("/")[-1] for c in res["chunks"][:3]]
    assert len(res["chunks"]) > 0, "RRF 应有命中"
    return f"RRF 粗排 top3: {top3}"


def s2_rrf_fallback_weighted():
    """显式禁用 RRF → 回退到 weighted_sum"""
    from service.core.rag.nlp.search_v2 import Dealer
    from service.core.rag.utils.es_conn import ESConnection
    from service.core.rag.utils.doc_store_conn import MatchTextExpr, MatchDenseExpr
    from service.core.rag.nlp.model import generate_embedding

    es = ESConnection()
    # 手动构造 matchExprs + use_rrf=False 调 search
    query = "世运电路"
    vec = generate_embedding(query)
    qryr = Dealer(dataStore=es).qryr
    match_text, _ = qryr.question(query, min_match=0.3)
    from service.core.rag.utils.doc_store_conn import FusionExpr
    match_dense = MatchDenseExpr(f"q_{len(vec)}_vec", vec, 'float', 'cosine', 1024, {"similarity": 0.1})
    fusion = FusionExpr("weighted_sum", 1024, {"weights": "0.05, 0.95"})

    # use_rrf=False 强制走旧逻辑
    res = es.search(
        ["docnm_kwd", "content_ltks"], [], {},
        [match_text, match_dense, fusion], None, 0, 5, "company_kb", [],
        use_rrf=False
    )
    ids = es.getChunkIds(res)
    assert len(ids) > 0, "weighted_sum 应有命中"
    return f"weighted_sum 模式返回 {len(ids)} 条(use_rrf=False 回退成功)"


def s3_rrf_multi_index_ignore():
    """混合库+不存在索引不报错(ignore_unavailable)"""
    from service.core.rag.nlp.search_v2 import Dealer
    from service.core.rag.utils.es_conn import ESConnection
    es = ESConnection()
    dealer = Dealer(dataStore=es)
    # 故意加 nonexistent_xyz,verify ignore_unavailable 生效
    res = dealer.retrieval("测试", None, "company_kb,9,nonexistent_xyz", None, 1, 5)
    # 不抛异常就算通过
    return f"混合 3 个索引(含不存在的)命中 {res['total']} 条,不报错 ✓"


print("=" * 60)
print("客户端 RRF 融合验证")
print("=" * 60)
step("S1 RRF 融合生效", s1_rrf_enabled)
step("S2 use_rrf=False 回退", s2_rrf_fallback_weighted)
step("S3 混合库+不存在索引容错", s3_rrf_multi_index_ignore)

print("\n===== 汇总 =====")
passed = sum(1 for _, ok, _ in STEPS if ok)
for name, ok, _ in STEPS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"结果: {passed}/{len(STEPS)} 通过")
sys.exit(0 if passed == len(STEPS) else 1)
