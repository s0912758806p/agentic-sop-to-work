# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Agentic Workflow 編排層：依 flow.json 的順序串接各 skill；run-scoped manifest；人核准 STOP。
步驟執行器在 lib/engine.py（run_step / run_map / print_plan）。退出碼：0 = 完成（DRAFT）；2 = 失敗。"""
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

    print(f"flow={flow['name']} run={rid}")

    name2idx = {}
    for idx, st in enumerate(flow["steps"]):
        key = st.get("id") or st.get("skill")
        if key and key not in name2idx:
            name2idx[key] = idx

    steps = []
    last_out = None

    def _fail(label, err):
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "failed_step": label,
                "error": (err or "")[-1000:], "steps": steps,
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
            if goto is None:
                _fail(f"branch@{i}", f"branch: no usable case ｜ 無可用分支：{why}")
            if goto not in name2idx:
                _fail(f"branch@{i}", f"branch goto {goto!r}: no such step ｜ 指向不存在的步驟")
            target = name2idx[goto]
            if target <= i:
                _fail(f"branch@{i}", f"branch goto {goto!r}: must be forward-only ｜ 必須往前")
            steps.append({"skill": f"branch→{goto}", "ok": True, "out": art, "error": ""})
            print(f"  [BRANCH] → {goto}")
            i = target
            continue
        op = resolve(st["out"])
        ok, err = run_step(st, resolve, inp, a.allow_mutations)
        if ok and st.get("gate"):
            ok2, gerr = gates.run_gate(st["gate"]["type"], kit.read_artifact(op), st["gate"].get("args"))
            if not ok2:
                ok, err = False, f"gate {st['gate']['type']} failed ｜ 閘門未過: {gerr}"
        label = st.get("skill") or ("cmd: " + (st.get("cmd", "")[:40] + ("…" if len(st.get("cmd", "")) > 40 else "")))
        steps.append({"skill": label, "ok": ok, "out": op, "error": (err or "")[:600]})
        print(f"  [{'OK' if ok else 'FAIL'}] {label} → {op}")
        if not ok:
            _fail(label, err)
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
