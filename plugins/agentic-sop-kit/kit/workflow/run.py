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
from flow import resolve_branch  # noqa: E402

FLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow.json")
BANNER = "DRAFT — 範例流程產出，需人員覆核；本 kit 永不自動歸檔進任何受控系統。"


def _run_map(st, tool, ip, op):
    """Run `tool` once per item of the top-level list `st['map_over']` in the input artifact's data;
    collect each output's data into a map@1 artifact. Fail-loud on any item failure (no silent drop)."""
    src = kit.read_artifact(ip) if os.path.exists(ip) else {}
    items = (src.get("data") or {}).get(st["map_over"])
    if not isinstance(items, list):
        return False, f"map_over '{st['map_over']}' is not a list（input data 內非清單）"
    base = os.path.dirname(op)
    name = st.get("skill", "map")
    results, trace = [], []
    for idx, item in enumerate(items):
        item_in = os.path.join(base, f"{name}.item{idx}.in.json")
        item_out = os.path.join(base, f"{name}.item{idx}.out.json")
        kit.write_artifact(kit.artifact("map-item@1", "map", item, []), item_in)
        r = subprocess.run([sys.executable, tool, "--in", item_in, "--out", item_out],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(item_out):
            return False, f"map item {idx} 失敗：{(r.stderr or r.stdout or '').strip()[-300:]}"
        out_art = kit.read_artifact(item_out)
        results.append(out_art.get("data"))
        trace.extend(out_art.get("trace", []))
    kit.write_artifact(kit.artifact("map@1", name, {"items": results, "count": len(results)}, trace), op)
    return True, ""


def _run_step(st, resolve, inp, allow_mutations):
    """Run one step (tool or cmd). Returns (ok, error)."""
    op = resolve(st["out"])
    if "cmd" in st:
        if st.get("mutates") and not allow_mutations:
            return False, ("此步驟標記 mutates:true（會改動環境）。"
                           "請人工確認後加 --allow-mutations 重跑。指令：" + st["cmd"])
        r = subprocess.run(st["cmd"], shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  [WARN] cmd exited {r.returncode} — attach a cmd_gate to enforce exit==0")
        kit.write_artifact(kit.artifact("cmd@1", "cmd",
                           {"command": st["cmd"], "exit": r.returncode,
                            "stdout": (r.stdout or "")[-4000:], "stderr": (r.stderr or "")[-4000:]}), op)
        return True, ""   # cmd always records; cmd_gate decides pass/fail
    tool, ip = kit.kit_path(st["tool"]), resolve(st["in"])
    if "map_over" in st:
        return _run_map(st, tool, ip, op)
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

    with open(a.flow, encoding="utf-8") as f:
        flow = json.load(f)

    if a.plan:
        _print_plan(flow)
        raise SystemExit(0)

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
        print("  ❌ 步驟失敗：", (err or "")[:300])
        raise SystemExit(2)

    i, n = 0, len(flow["steps"])
    while i < n:
        st = flow["steps"][i]
        if "branch" in st:
            art = resolve(st["branch"])
            data = kit.read_artifact(art).get("data", {}) if os.path.exists(art) else {}
            goto, why = resolve_branch(st.get("cases", []), data)
            if goto is None:
                _fail(f"branch@{i}", f"branch 無可用分支：{why}")
            if goto not in name2idx:
                _fail(f"branch@{i}", f"branch goto 指向不存在的步驟：{goto!r}")
            target = name2idx[goto]
            if target <= i:
                _fail(f"branch@{i}", f"branch goto 必須往前（forward-only）：{goto!r}")
            steps.append({"skill": f"branch→{goto}", "ok": True, "out": art, "error": ""})
            print(f"  [BRANCH] → {goto}")
            i = target
            continue
        op = resolve(st["out"])
        ok, err = _run_step(st, resolve, inp, a.allow_mutations)
        if ok and st.get("gate"):
            ok2, gerr = gates.run_gate(st["gate"]["type"], kit.read_artifact(op), st["gate"].get("args"))
            if not ok2:
                ok, err = False, f"gate {st['gate']['type']} failed: {gerr}"
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
