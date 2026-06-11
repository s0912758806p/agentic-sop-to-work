# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Engine step executors for the workflow runner: run one step (tool/cmd), map over a list,
and print a dry-run plan with static validation. Pure stdlib + kit; no LLM."""
import os
import subprocess
import sys

import kit  # noqa: E402  (lib/ is on sys.path — the runner inserts it before importing this module)


def run_map(st, tool, ip, op):
    """Run `tool` once per item of the top-level list `st['map_over']` in the input artifact's data;
    collect each output's data into a map@1 artifact. Fail-loud on any item failure (no silent drop)."""
    src = kit.read_artifact(ip) if os.path.exists(ip) else {}
    items = (src.get("data") or {}).get(st["map_over"])
    if not isinstance(items, list):
        return False, f"map_over '{st['map_over']}' is not a list ｜ input data 內非清單"
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
            return False, f"map item {idx} failed ｜ 失敗：{(r.stderr or r.stdout or '').strip()[-300:]}"
        out_art = kit.read_artifact(item_out)
        results.append(out_art.get("data"))
        trace.extend(out_art.get("trace", []))
    kit.write_artifact(kit.artifact("map@1", name, {"items": results, "count": len(results)}, trace), op)
    return True, ""


def run_step(st, resolve, inp, allow_mutations):
    """Run one step (tool or cmd). Returns (ok, error)."""
    op = resolve(st["out"])
    if "cmd" in st:
        if st.get("mutates") and not allow_mutations:
            return False, ("step is marked mutates:true (modifies the environment); re-run with "
                           "--allow-mutations after human review ｜ 會改動環境，人工確認後加 --allow-mutations 重跑. "
                           "cmd: " + st["cmd"])
        r = subprocess.run(st["cmd"], shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  [WARN] cmd exited {r.returncode} — attach a cmd_gate to enforce exit==0 ｜ 加 cmd_gate 強制 exit==0")
        kit.write_artifact(kit.artifact("cmd@1", "cmd",
                           {"command": st["cmd"], "exit": r.returncode,
                            "stdout": (r.stdout or "")[-4000:], "stderr": (r.stderr or "")[-4000:]}), op)
        return True, ""
    tool, ip = kit.kit_path(st["tool"]), resolve(st["in"])
    if "map_over" in st:
        return run_map(st, tool, ip, op)
    r = subprocess.run([sys.executable, tool, "--in", ip, "--out", op], capture_output=True, text=True)
    ok = (r.returncode == 0) and os.path.exists(op)
    return ok, (r.stderr or r.stdout or "").strip()


def print_plan(flow):
    """List every operation without executing; statically validate branch gotos.
    Returns an exit code: 0 = clean, 2 = structural problem(s) found."""
    steps = flow["steps"]
    name2idx, dups = {}, []
    for idx, st in enumerate(steps):
        key = st.get("id") or st.get("skill")
        if key:
            if key in name2idx:
                dups.append(key)
            else:
                name2idx[key] = idx
    print(f"PLAN flow={flow['name']} (dry run — nothing executed)")
    problems = []
    for i, st in enumerate(steps):
        n = i + 1
        if "branch" in st:
            print(f"  {n}. branch (reads {st['branch']}):")
            for c in st.get("cases", []):
                goto = c.get("goto")
                cond = "default" if c.get("default") else f"when {c.get('when')}"
                disp = goto if goto is not None else "(missing 'goto')"
                if goto is None:
                    tag = "  ✗ missing goto"
                    problems.append(f"step {n}: a case is missing its 'goto' key")
                elif goto not in name2idx:
                    tag = "  ✗ unknown goto"
                    problems.append(f"step {n} goto {goto!r}: no such step")
                elif name2idx[goto] <= i:
                    tag = "  ✗ not forward-only"
                    problems.append(f"step {n} goto {goto!r}: not forward-only")
                elif goto in dups:
                    tag = "  ✗ ambiguous (duplicate name)"
                    problems.append(f"step {n} goto {goto!r}: ambiguous — duplicate step name")
                else:
                    tag = ""
                print(f"       {cond} → {disp}{tag}")
        elif "cmd" in st:
            mut = "  [MUTATES — needs --allow-mutations]" if st.get("mutates") else ""
            print(f"  {n}. cmd: {st['cmd']}{mut}")
        elif "tool" in st:
            mp = f"  [map_over={st['map_over']!r} · per-item]" if "map_over" in st else ""
            print(f"  {n}. tool: {st['tool']}{mp}")
        else:
            tag = "  ✗ malformed (no tool/cmd/branch)"
            problems.append(f"step {n}: has no tool/cmd/branch key")
            print(f"  {n}.{tag}")
        if st.get("gate"):
            print(f"       gate: {st['gate']['type']}")
    if problems:
        print("  ⚠️ structural problems:")
        for p in problems:
            print(f"    - {p}")
        return 2
    return 0
