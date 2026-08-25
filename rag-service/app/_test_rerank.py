# -*- coding: utf-8 -*-
"""
SiliconFlow 精排模型单元测试:验证 siliconflow_rerank() 打分与降级。

验证点:
  A. 相关文档得分 > 无关文档
  B. 缺 API key / 错误 model 时返回 None(触发上层 fallback)
"""
import os
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


def s1_rerank_semantic():
    """相关文档打分应显著高于无关文档"""
    from service.core.rag.nlp.model import siliconflow_rerank
    query = "世运电路的营收情况"
    docs = [
        "世运电路2023年上半年营收同比增长20%,归母净利润达到1.2亿元",  # 高相关
        "今天天气不错,适合出门散步",                                       # 无关
        "世运电路是一家专业的PCB制造企业,主营高端印制电路板",             # 中等相关(实体但话题偏)
    ]
    scores = siliconflow_rerank(query, docs, top_n=3)
    assert scores is not None, "API 应返回 scores(检查 key/网络)"
    assert len(scores) == 3, f"scores 长度应等于 docs: 期望 3 得 {len(scores)}"
    assert scores[0] > scores[1], f"高相关分应大于无关分: {scores}"
    assert scores[2] > scores[1], f"中等相关应高于无关: {scores}"
    return f"scores={[round(s,4) for s in scores]}(相关>无关 ✓)"


def s2_rerank_fallback_no_key():
    """临时清 API key,应返回 None 触发上层 fallback"""
    from service.core.rag.nlp.model import siliconflow_rerank
    saved = os.environ.pop("DASHSCOPE_API_KEY", None)
    try:
        r = siliconflow_rerank("test", ["a", "b"], top_n=2)
        assert r is None, f"缺 API key 时应返回 None,实际={r}"
        return "缺 key → 返回 None(fallback 触发条件成立)"
    finally:
        if saved:
            os.environ["DASHSCOPE_API_KEY"] = saved


def s3_rerank_bad_model():
    """伪造 model 名应触发 404,返回 None"""
    from service.core.rag.nlp.model import siliconflow_rerank
    saved = os.environ.get("RERANK_MODEL")
    os.environ["RERANK_MODEL"] = "invalid/nonexistent-model-xyz"
    try:
        r = siliconflow_rerank("test", ["a", "b"], top_n=2)
        assert r is None, f"错误 model 应返回 None,实际={r}"
        return "错误 model → 返回 None(HTTP 4xx 被 catch)"
    finally:
        if saved:
            os.environ["RERANK_MODEL"] = saved
        else:
            os.environ.pop("RERANK_MODEL", None)


def s4_rerank_empty():
    """空文档列表应返回 []"""
    from service.core.rag.nlp.model import siliconflow_rerank
    r = siliconflow_rerank("q", [], top_n=5)
    assert r == [], f"空 docs 应返回 [],实际={r}"
    return "空 docs → []"


print("=" * 60)
print("SiliconFlow rerank 单元测试")
print("=" * 60)
step("S1 相关性打分正确", s1_rerank_semantic)
step("S2 缺 API key → None", s2_rerank_fallback_no_key)
step("S3 错误 model → None", s3_rerank_bad_model)
step("S4 空 docs → []", s4_rerank_empty)

print("\n===== 汇总 =====")
passed = sum(1 for _, ok, _ in STEPS if ok)
for name, ok, _ in STEPS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"结果: {passed}/{len(STEPS)} 通过")
sys.exit(0 if passed == len(STEPS) else 1)
