"""自動回歸驗證腳本（任務 2 核心）。被 Stop hook 觸發，也可手動執行。

流程：
  1. 交叉比對 registry.json vs workflow/flow.json：任何 flow 用到卻未登記測試的 skill → fail-loud（exit 3）。
  2. 變更偵測（內容雜湊快照 .verify_state.json；不依賴 git，跨環境可用）：
     自上次「通過」後，SOP/任一 skill 目錄/編排層皆無變動 → 直接結束、不跑測試（exit 0）。
  3. 有變動 → 跑兩層：
       單元層＝受影響 skill 各自的測試（哪個 skill 目錄/測試變了就跑哪個；動到 lib/workflow/registry 等共用層則全跑）；
       整合層＝整條 workflow 串接 + 交接資料正確（恆跑）。
  4. 寫回歸紀錄 regression_log.jsonl（時間、變更項、pass/fail、指標）。
  5. 判定：所有測試 pass = 正常（exit 0，且更新快照）；任一 fail = exit 2（不更新快照，讓修好後自動重跑）。
     「更好」指標（步數/執行時間/成功率）只記入 log，不作為通過與否的判據。

旗標：--all（忽略變更偵測，全跑；用於首次建立基線 / 人工全量驗證）。
退出碼：0 = 通過或無變更；2 = 有測試失敗；3 = 登錄表/基礎設施錯誤。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(KIT, "tests", "registry.json")
STATE = os.path.join(KIT, "tests", ".verify_state.json")
LOG = os.path.join(KIT, "tests", "regression_log.jsonl")

# 變更偵測時忽略的（產生物 / 快取 / 紀錄）——它們變動不代表「功能」變動。
_SKIP_DIRS = {"runs", "__pycache__", ".git", ".pytest_cache"}
_SKIP_RELS = {"tests/.verify_state.json", "tests/.retry_count", "tests/regression_log.jsonl"}
# 不論登錄表如何設定，動到登錄表本身一律全跑（它決定了「要跑什麼」）。
_ALWAYS_FORCE_ALL = {"tests/registry.json"}


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _sha(full):
    h = hashlib.sha256()
    with open(full, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot():
    """KIT 下所有來源檔的 {相對路徑: sha256}，排除產生物/快取/紀錄。"""
    snap = {}
    for root, dirs, files in os.walk(KIT):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fn in files:
            if fn.endswith(".pyc") or fn == ".DS_Store":
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, KIT).replace(os.sep, "/")
            if rel in _SKIP_RELS or os.path.basename(rel).startswith("."):
                continue
            try:
                snap[rel] = _sha(full)
            except OSError:
                pass
    return snap


def _flow_skills():
    flow = _load(os.path.join(KIT, "workflow", "flow.json"), {"steps": []})
    seen, out = set(), []
    for st in flow.get("steps", []):
        s = st.get("skill")
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out, len(flow.get("steps", []))


def _is_force_all(rel, watch):
    """動到共用層（registry.integration.watch 列的目錄/檔，如 lib/、workflow/、SOP.md）→ 全部單元 + 整合全跑。"""
    if rel in _ALWAYS_FORCE_ALL:
        return True
    for w in watch:
        w = w.rstrip("/")
        if rel == w or rel.startswith(w + "/"):
            return True
    return False


def _run_test(rel):
    full = os.path.join(KIT, rel)
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, full], cwd=KIT, capture_output=True, text=True)
    sec = time.perf_counter() - t0
    out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
    return (r.returncode == 0), round(sec, 3), out.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description="agentic-sop-kit 自動回歸驗證")
    ap.add_argument("--all", action="store_true", help="忽略變更偵測，全量跑（建立基線/人工驗證）")
    args = ap.parse_args(argv)

    reg = _load(REG, None)
    if reg is None:
        print(f"❌ 找不到/無法解析受測功能登錄表：{REG}", file=sys.stderr)
        return 3
    skills = reg.get("skills", {})
    integration = reg.get("integration", {})

    # (1) 交叉比對：flow 用到的每個 skill 都必須登記測試（防「納入新 skill 卻忘了登記測試」）。
    flow_skills, n_steps = _flow_skills()
    unregistered = [s for s in flow_skills if s not in skills]
    if unregistered:
        print("❌ 下列 skill 在 workflow/flow.json 被使用，但未登記單元測試於 tests/registry.json：\n  - "
              + "\n  - ".join(unregistered)
              + "\n請為每個 skill 補單元測試並登記（受測功能登錄表規則）。", file=sys.stderr)
        return 3
    # 每個登記的 skill 至少要有 1 支單元測試（防「登記了卻空著」的空洞登錄）。
    empty = [name for name, s in skills.items() if not s.get("tests")]
    if empty:
        print("❌ 下列 skill 已登記但未附任何單元測試（受測功能登錄表要求每個 skill ≥1 測試）：\n  - "
              + "\n  - ".join(empty), file=sys.stderr)
        return 3
    # 整合層不可缺（任務要求兩層測試）。
    if not integration.get("tests"):
        print("❌ 登錄表未登記任何整合測試（integration.tests 為空）；整合層不可缺。", file=sys.stderr)
        return 3
    # 登記的測試檔必須存在。
    declared = [t for s in skills.values() for t in s.get("tests", [])] + list(integration.get("tests", []))
    missing = [t for t in declared if not os.path.exists(os.path.join(KIT, t))]
    if missing:
        print("❌ 登錄表登記的測試檔不存在：\n  - " + "\n  - ".join(missing), file=sys.stderr)
        return 3

    # (2) 變更偵測
    prev = _load(STATE, {})
    prev_files = prev.get("files", {})
    cur_files = _snapshot()
    changed = sorted(k for k in set(prev_files) | set(cur_files)
                     if prev_files.get(k) != cur_files.get(k))
    first_run = not prev_files
    if not args.all and not first_run and not changed:
        print(f"✔ 無變更（自上次驗證 {prev.get('ts', '?')}，verdict={prev.get('verdict', '?')}）— 略過測試。")
        return 0

    # (3) 決定受影響 skill + 要跑的測試（共用層由 registry.integration.watch 設定，config-driven）
    watch = integration.get("watch", [])
    force_all = args.all or first_run or any(_is_force_all(c, watch) for c in changed)
    if force_all:
        affected = list(skills.keys())
    else:
        affected = []
        for name, s in skills.items():
            sdir = s.get("dir", "").rstrip("/") + "/"
            tests = set(s.get("tests", []))
            if any(c == t for c in changed for t in tests) or any(c.startswith(sdir) for c in changed):
                affected.append(name)
    unit_tests = [t for name in affected for t in skills[name].get("tests", [])]
    integration_tests = list(integration.get("tests", []))

    trigger = "all" if args.all else ("first_run" if first_run else "change")
    print(f"▶ 回歸驗證 trigger={trigger} 變更={len(changed)} 受影響 skill={affected or '—'}")

    # (4) 跑兩層
    def _layer(rels):
        res = []
        for rel in rels:
            ok, sec, out = _run_test(rel)
            res.append({"test": rel, "passed": ok, "seconds": sec, "output": out})
            print(f"  [{'PASS' if ok else 'FAIL'}] {rel}  ({sec}s)")
        return res

    t_all = time.perf_counter()
    unit_res = _layer(unit_tests)
    integ_res = _layer(integration_tests)
    total_sec = round(time.perf_counter() - t_all, 3)

    all_res = unit_res + integ_res
    passed = all(r["passed"] for r in all_res)
    n_pass = sum(1 for r in all_res if r["passed"])
    verdict = "pass" if passed else "fail"

    # 指標（趨勢用，僅記 log，不作判據）
    metrics = {
        "total_seconds": total_sec,
        "unit_seconds": round(sum(r["seconds"] for r in unit_res), 3),
        "integration_seconds": round(sum(r["seconds"] for r in integ_res), 3),
        "tests_run": len(all_res),
        "tests_passed": n_pass,
        "success_rate": round(n_pass / len(all_res), 3) if all_res else 1.0,
        "workflow_steps": n_steps,
    }

    # 回歸紀錄（一行 JSON；不存大量 output，僅留測試清單與結果）
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "trigger": trigger,
        "changed": changed,
        "affected_skills": affected,
        "unit": [{k: r[k] for k in ("test", "passed", "seconds")} for r in unit_res],
        "integration": [{k: r[k] for k in ("test", "passed", "seconds")} for r in integ_res],
        "verdict": verdict,
        "metrics": metrics,
    }
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"WARNING: 無法寫入回歸紀錄 {LOG}: {e}", file=sys.stderr)

    # (5) 判定 + 快照更新
    print(f"— verdict={verdict}  通過 {n_pass}/{len(all_res)}  指標 {json.dumps(metrics, ensure_ascii=False)}")
    if passed:
        try:
            with open(STATE, "w", encoding="utf-8") as f:
                json.dump({"ts": entry["ts"], "verdict": "pass", "files": cur_files}, f, ensure_ascii=False)
        except OSError as e:
            print(f"WARNING: 無法更新驗證快照 {STATE}: {e}", file=sys.stderr)
        return 0

    # 失敗：不更新快照（保留上次「通過」基線 → 修好後內容再變、自動重跑）。輸出失敗詳情供 hook 餵回。
    print("\n===== 回歸失敗詳情（供修正參考）=====")
    for r in all_res:
        if not r["passed"]:
            print(f"\n### FAIL: {r['test']}\n{r['output'][-3000:]}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
