# -*- coding: utf-8 -*-
"""
RAG 全链路端到端测试:解析→切分→向量化→建索引(dense_vector)→入库→检索命中。
用一个全新临时索引,跑完自动删除,不污染现有 company_kb / 用户库数据。
逐步打印证据,最后汇总 PASS/FAIL。退出码 0=全过。
"""
import sys, traceback

TEST_INDEX = "e2e_test_probe"          # 临时索引,跑完删除
PDF = "/app/service/core/storage/file/1/【兴证电子】世运电路2023中报点评.pdf"
QUERY = "世运电路 业绩 营收 归母净利润"

STEPS = []
def step(name, fn):
    try:
        detail = fn()
        STEPS.append((name, True, detail))
        print(f"[PASS] {name} :: {detail}")
        return detail
    except Exception as e:
        STEPS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {name} :: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None

# 共享状态
STATE = {}

def s1_parse():
    """解析 + 切分:PDF → 若干文本段"""
    from service.core.file_parse import parse
    docs = parse(PDF)
    assert isinstance(docs, list) and len(docs) > 0, f"解析返回空: {docs}"
    STATE["docs"] = docs
    sample = docs[0].get("content_with_weight", "")[:60]
    return f"切分 {len(docs)} 段; 首段: {sample}..."

def s2_vectorize():
    """向量化:每段生成 q_1024_vec(调 SiliconFlow embedding)"""
    from service.core.file_parse import process_items
    processed = process_items(STATE["docs"], "e2e_世运电路.pdf", TEST_INDEX)
    assert processed, "process_items 返回空(向量化失败,可能 embedding API 不通)"
    # 找向量字段
    vec_keys = [k for k in processed[0].keys() if k.startswith("q_") and k.endswith("_vec")]
    assert vec_keys, f"首段无向量字段: {list(processed[0].keys())}"
    dim = len(processed[0][vec_keys[0]])
    assert dim == 1024, f"向量维度异常: {vec_keys[0]}={dim} 期望 1024"
    STATE["processed"] = processed
    return f"{len(processed)} 段全部向量化; 向量字段={vec_keys[0]} 维度={dim}"

def s3_ensure_index():
    """建索引:按 mapping.json 创建,q_1024_vec 必须是 dense_vector"""
    from service.core.rag.utils.es_conn import ESConnection
    es = ESConnection()
    STATE["es"] = es
    # 先删干净(防止上次残留)
    if es.es.indices.exists(index=TEST_INDEX):
        es.es.indices.delete(index=TEST_INDEX)
    es._ensure_index(TEST_INDEX)
    assert es.es.indices.exists(index=TEST_INDEX), "索引创建失败"
    # 校验 mapping:q_1024_vec 是否 dense_vector
    mp = es.es.indices.get_mapping(index=TEST_INDEX)
    props = mp[TEST_INDEX]["mappings"].get("properties", {})
    dyn = mp[TEST_INDEX]["mappings"].get("dynamic_templates", [])
    has_dense_template = any(
        "dense_vector" in str(t) and "1024" in str(t) for t in dyn
    )
    assert has_dense_template, f"缺 *_1024_vec→dense_vector 动态模板: dynamic_templates={dyn}"
    return f"索引 {TEST_INDEX} 已建; dynamic_templates 含 *_1024_vec→dense_vector(向量检索地基 ok)"

def s4_insert():
    """入库:bulk 写入 ES,无失败项"""
    es = STATE["es"]
    errors = es.insert(documents=STATE["processed"], indexName=TEST_INDEX)
    assert not errors, f"bulk 入库有失败项: {errors}"
    es.es.indices.refresh(index=TEST_INDEX)
    cnt = es.es.count(index=TEST_INDEX)["count"]
    assert cnt == len(STATE["processed"]), f"入库条数不符: ES={cnt} 期望={len(STATE['processed'])}"
    # 确认写入文档确实带 dense_vector(取一条看字段)
    hit = es.es.search(index=TEST_INDEX, size=1)["hits"]["hits"][0]["_source"]
    vec_keys = [k for k in hit.keys() if k.startswith("q_") and k.endswith("_vec")]
    assert vec_keys, f"入库文档无向量字段: {list(hit.keys())}"
    return f"入库 {cnt} 条; 文档含向量字段 {vec_keys[0]}(len={len(hit[vec_keys[0]])})"

def s5_retrieve():
    """检索:向量+关键词混合检索,命中刚入库的内容"""
    from service.core.retrieval import retrieve_content
    res = retrieve_content(TEST_INDEX, QUERY)
    assert isinstance(res, list) and len(res) > 0, f"检索无命中: {res}"
    top = res[0]
    docname = top.get("document_name", "?")
    content = top.get("content", "")[:60]
    return f"检索命中 {len(res)} 条; TOP1 文档={docname}; 内容: {content}..."

def s6_merge_retrieve():
    """合并检索:company_kb + 临时索引 多库合并(验证逗号多索引 + 缺失容错)"""
    from service.core.retrieval import retrieve_content
    # 故意混入一个不存在的索引,验证 ignore_unavailable 容错
    res = retrieve_content(f"company_kb,{TEST_INDEX},nonexistent_idx_xyz", QUERY)
    assert isinstance(res, list), f"合并检索返回非 list: {type(res)}"
    docs = {r.get("document_name", "?") for r in res}
    return f"合并检索(含不存在索引)命中 {len(res)} 条不报错; 文档集={list(docs)[:4]}"

def cleanup():
    """删除临时测试索引,不留痕"""
    try:
        es = STATE.get("es")
        if es and es.es.indices.exists(index=TEST_INDEX):
            es.es.indices.delete(index=TEST_INDEX)
            return f"已删除临时索引 {TEST_INDEX}"
        return "无需清理"
    except Exception as e:
        return f"清理失败(需手动删 {TEST_INDEX}): {e}"


print("=" * 60)
print("RAG 全链路端到端测试:解析→切分→向量化→建索引→入库→检索")
print("=" * 60)
step("S1 解析+切分 PDF", s1_parse)
step("S2 向量化(q_1024_vec)", s2_vectorize)
step("S3 建索引(dense_vector 地基)", s3_ensure_index)
step("S4 入库 ES(bulk)", s4_insert)
step("S5 检索命中(单库)", s5_retrieve)
step("S6 合并检索+缺失容错", s6_merge_retrieve)

print("\n----- 清理 -----")
print(cleanup())

print("\n===== 端到端汇总 =====")
passed = sum(1 for _, ok, _ in STEPS if ok)
for name, ok, _ in STEPS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"结果: {passed}/{len(STEPS)} 通过")
sys.exit(0 if passed == len(STEPS) else 1)
