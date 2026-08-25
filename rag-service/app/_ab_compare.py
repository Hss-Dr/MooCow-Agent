# -*- coding: utf-8 -*-
"""
检索链路 A/B 对比:旧(weighted_sum + 本地 hybrid_similarity) vs 新(RRF + SiliconFlow rerank)

数据基础:company_kb 25 段,来自《世运电路 2023 中报点评》PDF。
段落分类(人工看过):
  - 业务段(BUSINESS):2,5,6,7,8,14,15,17,18,19,20,21,22  → 有效财务/业务事实
  - 噪音段(NOISE   ):1,3,4,9,10,11,12,13,16,23,24,25    → 表格头/免责声明/合规套话

评估:
  - top5 段号(便于目视对比)
  - top5 里业务段命中数(越高越好,理想=5)
  - top1 是否是业务段
"""
import sys

# 首先枚举段号 → segment_id 映射(id 是 ES 里的 _id,通常是 chunk hash;段号是按检索顺序)
# 但我们其实在 ES 里不知道文本→段号映射,需要用文本前 30 字识别
# 直接改用命中文本前 20 字判断类别更简单

# 段号 → 类别(1-indexed,按前面 ES search size=25 的顺序)
# 但顺序不是稳定的(ES 返回顺序不固定),我们用「内容开头前缀 → 类别」判定更稳
BUSINESS_PREFIXES = [
    "主要财务指标",           # 段2
    "主要财务比率",           # 段5
    "投资评级说明",           # 段6
    "公司研证券研究报告",     # 段7
    "s司点评报告终端需求疲软",  # 段8
    "利润表单位",             # 段14
    "归母净利润",             # 段15
    "产品结构优化",           # 段17
    "relatedR相关报告",       # 段18
    "费用方面",               # 段19
    "告：电动化、智能化",       # 段20
    "emailA分析师",           # 段21
    "风险提示",               # 段22
]
NOISE_PREFIXES = [
    "market",                # 段1(市场数据)
    "现金流量表",             # 段3
    "附表",                   # 段4(资产负债表头)
    "本报告仅供",             # 段9
    "本报告所载资料",         # 段10
    "本报告并非针对",         # 段11
    "特别声明",               # 段12
    "兴业证券研究",           # 段13
    "15层",                   # 段16
    "信息披露",               # 段23
    "除非另行说明",           # 段24
    "本报告的版权",           # 段25
]

def classify(content: str) -> str:
    # 去掉 <table> 标签取纯文本前 40 字
    import re
    txt = re.sub(r"<[^>]+>", "", content)[:40].strip()
    for p in BUSINESS_PREFIXES:
        if p in txt or txt.startswith(p):
            return "B"  # Business
    for p in NOISE_PREFIXES:
        if p in txt or txt.startswith(p):
            return "N"  # Noise
    return "?"  # Unknown


# 10 个 Query,聚焦业务问题
QUERIES = [
    "世运电路2023上半年营收下降的原因",              # 期望命中段8
    "公司2023年上半年毛利率的变化情况",              # 期望命中段17
    "特斯拉汽车电子PCB供应关系",                     # 期望命中段20
    "归母净利润未来三年预测数据",                    # 期望命中段2/15/21
    "汇兑收益对利润的贡献",                          # 期望命中段19
    "投资建议和目标评级",                            # 期望命中段6/21
    "汽车销量下滑和新能源渗透的风险提示",             # 期望命中段22
    "车用PCB在新能源和数通领域的需求增长",           # 期望命中段20
    "产品结构优化 高附加值产品占比",                 # 期望命中段17
    "兴证电子相关研究报告 2022年报点评",             # 期望命中段18
]


def run_query(dealer, query, use_rrf: bool, rerank_mdl, sim_thresh: float = 0.1):
    """跑单个查询,返回 top5 段落信息(通过 patch instance method 切换 use_rrf)。
    sim_thresh 默认与生产 (retrieval.py) 一致:0.1。
    如果要看「填满 top5」的形态,可临时传更低值(如 0.02),但生产不建议 —— 精度优先。
    """
    es_ds = dealer.dataStore
    orig_search = es_ds.search  # bound method,已含 self
    def wrapped(*args, **kwargs):
        kwargs['use_rrf'] = use_rrf
        return orig_search(*args, **kwargs)
    es_ds.search = wrapped
    try:
        res = dealer.retrieval(query, None, "company_kb", None, 1, 5,
                               similarity_threshold=sim_thresh, rerank_mdl=rerank_mdl)
    finally:
        es_ds.search = orig_search
    hits = []
    for c in res["chunks"]:
        content = c.get("content_with_weight", "")
        cat = classify(content)
        preview = content.replace("\n", " ")[:35]
        hits.append({"cat": cat, "preview": preview, "sim": c.get("similarity", 0)})
    return hits


def summarize(hits):
    biz = sum(1 for h in hits if h["cat"] == "B")
    top1_biz = "B" if hits and hits[0]["cat"] == "B" else "N"
    return biz, top1_biz


def print_query_result(i, q, old_hits, new_hits):
    ob, ot = summarize(old_hits)
    nb, nt = summarize(new_hits)
    diff_flag = "✓变优" if nb > ob else ("=" if nb == ob else "✗变差")
    print(f"\n[Q{i}] {q}")
    print(f"  ┌ 旧链路(weighted_sum+local)  top1={ot}  业务段命中={ob}/5")
    for j, h in enumerate(old_hits, 1):
        print(f"  │  [{j}] [{h['cat']}] {h['preview']}...")
    print(f"  └ 新链路(RRF+SiliconFlow )  top1={nt}  业务段命中={nb}/5  ({diff_flag})")
    for j, h in enumerate(new_hits, 1):
        print(f"     [{j}] [{h['cat']}] {h['preview']}...")


def main():
    from service.core.rag.nlp.search_v2 import Dealer
    from service.core.rag.utils.es_conn import ESConnection
    dealer = Dealer(dataStore=ESConnection())

    total_old_biz = 0
    total_new_biz = 0
    top1_old_biz = 0
    top1_new_biz = 0

    print("=" * 70)
    print("检索链路 A/B 对比:10 查询")
    print("=" * 70)

    for i, q in enumerate(QUERIES, 1):
        # 旧链路
        old_hits = run_query(dealer, q, use_rrf=False, rerank_mdl=None)
        # 新链路
        new_hits = run_query(dealer, q, use_rrf=True, rerank_mdl="siliconflow")
        print_query_result(i, q, old_hits, new_hits)

        ob, ot = summarize(old_hits)
        nb, nt = summarize(new_hits)
        total_old_biz += ob
        total_new_biz += nb
        if ot == "B": top1_old_biz += 1
        if nt == "B": top1_new_biz += 1

    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)
    print(f"top1 是业务段的次数    :  旧 {top1_old_biz}/10  vs  新 {top1_new_biz}/10")
    print(f"top5 业务段命中总数    :  旧 {total_old_biz}/50 vs  新 {total_new_biz}/50")
    print(f"业务命中率(总数百分比):  旧 {total_old_biz*2}%    vs  新 {total_new_biz*2}%")
    if total_new_biz > total_old_biz:
        gain = total_new_biz - total_old_biz
        print(f"\n新链路命中业务段 +{gain} 条(+{gain*2}%),质量提升")
    elif total_new_biz == total_old_biz:
        print("\n两链路命中数持平(数据规模小可能不足以拉开差距)")
    else:
        print(f"\n新链路命中业务段 -{total_old_biz - total_new_biz} 条(数据太少或参数需调)")


if __name__ == "__main__":
    main()
    sys.exit(0)
