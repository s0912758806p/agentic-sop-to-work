# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Agentic Workflow 編排層：依 flow.json 的順序串接各 skill；run-scoped manifest；人核准 STOP。
步驟執行器在 lib/engine.py（run_step / run_map / print_plan）。退出碼：0 = 完成（DRAFT）；2 = 失敗。

失敗時 manifest 帶機器可讀 `failure{step,gate_type,message,artifact}`，供上層定向修復。
`--max-fix-retries N`（預設讀 `SOPKIT_MAX_FIX_RETRIES`、否則 3；與 Stop-hook 回歸共用同一上限）對同一 `--run-id` 封頂自動修復重試：這支引擎只負責**程式強制的上限**
——同一 run-id 執行超過 1+N 次即拒跑、寫 `fix_exhausted`；實際的修復（重生/改輸入）由 `/sop-flow`
的 Claude 層執行，引擎本身維持零 LLM、確定性。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import kit  # noqa: E402
import gates  # noqa: E402
from flow import resolve_branch  # noqa: E402
from engine import run_step, print_plan  # noqa: E402

FLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow.json")
BANNER = "DRAFT — 範例流程產出，需人員覆核；本 kit 永不自動歸檔進任何受控系統。"


def main(argv=None):
    ap = argparse.ArgumentParser(description="agentic-sop-kit workflow runner")
    ap.add_argument("--flow", default=FLOW, help="flow.json path (default: bundled demo flow)")
    ap.add_argument("--input", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-base", default=None)
    ap.add_argument("--plan", action="store_true", help="list operations (and validate) without executing")
    ap.add_argument("--allow-mutations", action="store_true", help="authorize steps marked mutates:true")
    ap.add_argument("--max-fix-retries", type=int, default=int(os.environ.get("SOPKIT_MAX_FIX_RETRIES", "3")),
                    help="code-enforced ceiling on auto-fix re-runs per --run-id (default: $SOPKIT_MAX_FIX_RETRIES or 3, shared with the Stop-hook regression loop); "
                         "the fixing itself is done by the /sop-flow Claude layer, not here")
    a = ap.parse_args(argv)

    with open(a.flow, encoding="utf-8") as f:
        flow = json.load(f)

    if a.plan:
        raise SystemExit(print_plan(flow))

    inp = a.input or kit.kit_path(flow["input_default"])
    run = kit.run_dir(a.out_base, a.run_id)
    rid = os.path.basename(run)

    def resolve(v):
        return v.replace("$INPUT", inp).replace("$RUN", run)

    # --- code-enforced fix-loop ceiling (per run-id) -------------------------
    # The /sop-flow Claude layer auto-fixes by re-invoking with the SAME --run-id.
    # This counter caps total executions at 1 + max_fix_retries and refuses past it
    # — the real "封頂" lives in code, not in the prose of the command.
    counter_path = os.path.join(run, ".fix_attempts")
    prev = 0
    if os.path.exists(counter_path):
        try:
            prev = int(open(counter_path, encoding="utf-8").read().strip() or "0")
        except ValueError:
            prev = 0
    if prev > a.max_fix_retries:
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED",
                "fix_exhausted": True, "attempts": prev, "max_fix_retries": a.max_fix_retries,
                "error": f"fix-loop exhausted: {a.max_fix_retries} auto-fix retries used ｜ 自動修復已達上限，交人處理",
                "human_review_required": True, "banner": BANNER}
        kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
        print(f"  ⛔ fix-loop exhausted ({a.max_fix_retries} retries) — STOP, human needed ｜ 自動修復達上限，交人")
        raise SystemExit(2)
    with open(counter_path, "w", encoding="utf-8") as cf:
        cf.write(str(prev + 1))

    print(f"flow={flow['name']} run={rid} attempt={prev + 1}")

    name2idx = {}
    for idx, st in enumerate(flow["steps"]):
        key = st.get("id") or st.get("skill")
        if key and key not in name2idx:
            name2idx[key] = idx

    steps = []
    last_out = None

    def _fail(label, err, failure=None):
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "failed_step": label,
                "error": (err or "")[-1000:], "steps": steps,
                "failure": failure, "fix_attempt": prev + 1, "max_fix_retries": a.max_fix_retries,
                "human_review_required": True, "banner": BANNER}
        kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
        print("  ❌ step failed ｜ 步驟失敗：", (err or "")[:300])
        raise SystemExit(2)

    i, n = 0, len(flow["steps"])
    while i < n:
        st = flow["steps"][i]
        if "branch" in st:
            art = resolve(st["branch"])
            data = kit.read_artifact(art).get("data", {}) if os.path.exists(art) else {}
            goto, why = resolve_branch(st.get("cases", []), data)
            bfail = lambda msg: {"step": f"branch@{i}", "gate_type": None, "message": msg, "artifact": art}
            if goto is None:
                _fail(f"branch@{i}", f"branch: no usable case ｜ 無可用分支：{why}", bfail(why))
            if goto not in name2idx:
                _fail(f"branch@{i}", f"branch goto {goto!r}: no such step ｜ 指向不存在的步驟",
                      bfail(f"goto {goto!r}: no such step"))
            target = name2idx[goto]
            if target <= i:
                _fail(f"branch@{i}", f"branch goto {goto!r}: must be forward-only ｜ 必須往前",
                      bfail(f"goto {goto!r}: not forward-only"))
            steps.append({"skill": f"branch→{goto}", "ok": True, "out": art, "error": ""})
            print(f"  [BRANCH] → {goto}")
            i = target
            continue
        op = resolve(st["out"])
        ok, err = run_step(st, resolve, inp, a.allow_mutations)
        gate_type = None
        if ok and st.get("gate"):
            gate_type = st["gate"]["type"]
            ok2, gerr = gates.run_gate(gate_type, kit.read_artifact(op), st["gate"].get("args"))
            if not ok2:
                ok, err = False, f"gate {gate_type} failed ｜ 閘門未過: {gerr}"
        label = st.get("skill") or ("cmd: " + (st.get("cmd", "")[:40] + ("…" if len(st.get("cmd", "")) > 40 else "")))
        steps.append({"skill": label, "ok": ok, "out": op, "error": (err or "")[:600]})
        print(f"  [{'OK' if ok else 'FAIL'}] {label} → {op}")
        if not ok:
            _fail(label, err, {"step": label, "gate_type": gate_type,
                               "message": (err or "")[-1000:], "artifact": op})
        last_out = op
        i += 1

    final = last_out
    mani = {"flow": flow["name"], "run_id": rid, "state": "OK_FOR_REVIEW", "steps": steps,
            "final_output": final, "human_review_required": True, "banner": BANNER}
    kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
    print(f"  ✅ 流程完成 → {final}")
    print("  " + BANNER)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
