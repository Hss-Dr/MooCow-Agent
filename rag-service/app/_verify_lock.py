# -*- coding: utf-8 -*-
"""
测试镜像验证脚本:确认用 requirements.lock.txt 重建后,核心功能仍可用。
在测试容器(:testlock)内运行,连同一套 ES/PG/Redis。只读检索 + 纯解析,不写真实业务数据。
逐项打印 PASS/FAIL,最后汇总。退出码 0=全过,非 0=有失败。
"""
import sys, traceback

RESULTS = []
def check(name, fn):
    try:
        detail = fn()
        RESULTS.append((name, True, detail))
        print(f"[PASS] {name} :: {detail}")
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {name} :: {type(e).__name__}: {e}")
        traceback.print_exc()


def c1_versions():
    import numpy, cv2, xgboost
    assert numpy.__version__.startswith("1.26"), f"numpy={numpy.__version__} 期望 1.26.x"
    assert cv2.__version__.startswith("4.10"), f"opencv={cv2.__version__} 期望 4.10.x"
    assert xgboost.__version__.startswith("1.3"), f"xgboost={xgboost.__version__} 期望 1.3.x"
    # sklearn 应当不存在(已从代码移除,锁文件未含)
    try:
        import sklearn  # noqa
        raise AssertionError("sklearn 竟然存在,锁文件应当不含它")
    except ImportError:
        pass
    return f"numpy={numpy.__version__} opencv={cv2.__version__} xgboost={xgboost.__version__} sklearn=absent(ok)"


def c2_pipcheck():
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    # numpy<2 下 opencv 4.10 不应再报 numpy>=2 冲突
    bad = [ln for ln in out.splitlines() if "numpy" in ln.lower() and "has requirement" in ln.lower()]
    assert not bad, f"pip check 仍报 numpy 冲突: {bad}"
    return f"pip check ok (raw: {out[:120] or 'No broken requirements found.'})"


def c3_parse_pdf():
    # opencv 4.10 解析路径:纯 parse(),不写 ES、不调 embedding
    from service.core.file_parse import parse
    pdf = "/app/service/core/storage/file/1/【兴证电子】世运电路2023中报点评.pdf"
    docs = parse(pdf)
    assert isinstance(docs, list) and len(docs) > 0, f"parse 返回空: {type(docs)} len={len(docs) if hasattr(docs,'__len__') else 'n/a'}"
    return f"parse() 产出 {len(docs)} 段(opencv 4.10 解析链 ok)"


def c4_retrieval_merge():
    # 合并检索:复现之前修的 rerank 三 bug 场景(_as_tokens / numpy 余弦 / 本地 rerank)
    from service.core.retrieval import retrieve_content
    res = retrieve_content("company_kb,9", "世运电路 业绩 营收")
    assert isinstance(res, list), f"检索返回非 list: {type(res)}"
    idxs = {r.get("document_name", "?") for r in res}
    return f"合并检索 company_kb,9 命中 {len(res)} 条; 文档集={list(idxs)[:5]}"


def c5_jwt():
    # admin 门禁依赖的 token 结构:必须是 {subject:{user_id,...}}
    # 零依赖:手动 base64 解 payload 段(锁文件里没有 PyJWT,只有 python-jose)
    from service.auth import create_token
    import base64, json
    tok = create_token(8, "verify_admin")
    seg = tok.split(".")[1]
    seg += "=" * (-len(seg) % 4)  # 补 padding
    payload = json.loads(base64.urlsafe_b64decode(seg))
    assert "subject" in payload, f"payload 缺 subject: {list(payload.keys())}"
    assert payload["subject"].get("user_id") == 8, f"subject.user_id 错: {payload['subject']}"
    return f"create_token 结构正确: subject.user_id={payload['subject']['user_id']}"


check("C1 依赖版本(numpy/opencv/xgboost/sklearn)", c1_versions)
check("C2 pip check 无 numpy 冲突", c2_pipcheck)
check("C3 opencv4.10 解析真实 PDF", c3_parse_pdf)
check("C4 合并检索链(rerank 三修)", c4_retrieval_merge)
check("C5 admin 门禁 JWT 结构", c5_jwt)

print("\n===== 验证汇总 =====")
passed = sum(1 for _, ok, _ in RESULTS if ok)
for name, ok, detail in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"结果: {passed}/{len(RESULTS)} 通过")
sys.exit(0 if passed == len(RESULTS) else 1)
