# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Agentic Workflow 編排層：依 flow.json 的 SOP 順序，把各「單一工具 skill」串成完整流程（A→B→C）。

逐步以子程序執行各 skill（同一 python3），串接 artifact（上一步 out = 下一步 in），
產出 run-scoped 覆核包 `run_manifest.json`，最後 **人核准 STOP**。
任一步驟失敗（含缺依賴 → skill 內 require_deps 拋錯）→ **立即停止並回報該步 stderr**（明確報錯，非靜默）。
退出碼：0 = 流程完成（DRAFT 待覆核）；2 = 某步失敗。
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import kit  # noqa: E402
import gates  # noqa: E402

FLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow.json")
BANNER = "DRAFT — 範例流程產出，需人員覆核；本 kit 永不自動歸檔進任何受控系統。"


def _run_step(st, resolve, inp, allow_mutations):
    """Run one step (tool or cmd). Returns (ok, error)."""
    op = resolve(st["out"])
    if "cmd" in st:
        if st.get("mutates") and not allow_mutations:
            return False, ("此步驟標記 mutates:true（會改動環境）。"
                           "請人工確認後加 --allow-mutations 重跑。指令：" + st["cmd"])
        r = subprocess.run(st["cmd"], shell=True, capture_output=True, text=True)
        kit.write_artifact(kit.artifact("cmd@1", "cmd",
                           {"command": st["cmd"], "exit": r.returncode,
                            "stdout": (r.stdout or "")[-4000:], "stderr": (r.stderr or "")[-4000:]}), op)
        return True, ""   # cmd always records; cmd_gate decides pass/fail
    tool, ip = kit.kit_path(st["tool"]), resolve(st["in"])
    r = subprocess.run([sys.executable, tool, "--in", ip, "--out", op], capture_output=True, text=True)
    ok = (r.returncode == 0) and os.path.exists(op)
    return ok, (r.stderr or r.stdout or "").strip()


def _print_plan(flow):
    print(f"PLAN flow={flow['name']} (dry run — nothing executed)")
    for i, st in enumerate(flow["steps"], 1):
        if "cmd" in st:
            mut = " [MUTATES — needs --allow-mutations]" if st.get("mutates") else ""
            print(f"  {i}. cmd: {st['cmd']}{mut}")
        else:
            print(f"  {i}. tool: {st.get('tool')}")
        if st.get("gate"):
            print(f"       gate: {st['gate']['type']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="agentic-sop-kit workflow runner")
    ap.add_argument("--flow", default=FLOW, help="flow.json path (default: bundled demo flow)")
    ap.add_argument("--input", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-base", default=None)
    ap.add_argument("--plan", action="store_true", help="list operations without executing")
    ap.add_argument("--allow-mutations", action="store_true", help="authorize steps marked mutates:true")
    a = ap.parse_args(argv)

    flow = json.load(open(a.flow, encoding="utf-8"))

    if a.plan:
        _print_plan(flow)
        raise SystemExit(0)

    inp = a.input or kit.kit_path(flow["input_default"])
    run = kit.run_dir(a.out_base, a.run_id)
    rid = os.path.basename(run)

    def resolve(v):
        return v.replace("$INPUT", inp).replace("$RUN", run)

    print(f"flow={flow['name']} run={rid}")
    steps = []
    for st in flow["steps"]:
        op = resolve(st["out"])
        ok, err = _run_step(st, resolve, inp, a.allow_mutations)
        if ok and st.get("gate"):
            ok, gerr = gates.run_gate(st["gate"]["type"], kit.read_artifact(op), st["gate"].get("args"))
            if not ok:
                err = f"gate {st['gate']['type']} failed: {gerr}"
        label = st.get("skill") or ("cmd:" + st.get("cmd", "")[:40])
        steps.append({"skill": label, "ok": ok, "out": op, "error": (err or "")[:600]})
        print(f"  [{'OK' if ok else 'FAIL'}] {label} → {op}")
        if not ok:
            mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "failed_step": label,
                    "error": (err or "")[-1000:], "steps": steps,
                    "human_review_required": True, "banner": BANNER}
            kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
            print("  ❌ 步驟失敗：", (err or "")[:300])
            raise SystemExit(2)

    final = steps[-1]["out"]
    mani = {"flow": flow["name"], "run_id": rid, "state": "OK_FOR_REVIEW", "steps": steps,
            "final_output": final, "human_review_required": True, "banner": BANNER}
    kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
    print(f"  ✅ 流程完成 → {final}")
    print("  " + BANNER)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
