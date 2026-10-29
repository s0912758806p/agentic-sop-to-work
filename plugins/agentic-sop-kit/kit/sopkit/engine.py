# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Engine step executors for the workflow runner: run one step (tool/cmd), map over a list,
and print a dry-run plan with static validation. Pure stdlib + kit; no LLM.

A `cmd` is either a string (run through the shell; `$INPUT` / `$RUN` are substituted
shell-quoted) or a list of argv strings (run WITHOUT a shell; substituted verbatim per
element) — the list form is the one to use when an argument may contain spaces or quotes.
"""
import os
import shlex
import subprocess
import sys

from . import graph, kit
from .console import safe_print


def _quote(value):
    """Shell-quote one substituted value for the platform's shell."""
    if os.name == "nt":
        return subprocess.list2cmdline([value])
    return shlex.quote(value)


def cmd_display(cmd):
    """Human-readable form of a string or list cmd (plan output, step labels)."""
    return cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)


def substitute(value, inp, run, quote=False):
    """Replace $INPUT / $RUN. `quote` shell-quotes the substituted paths (string cmds)."""
    i, r = (_quote(inp), _quote(run)) if quote else (inp, run)
    return value.replace("$INPUT", i).replace("$RUN", r)


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


def run_step(st, resolve, inp, allow_mutations, run=None):
    """Run one step (tool or cmd). Returns (ok, error).

    `run` (the run dir) enables $INPUT/$RUN substitution inside a cmd; without it the cmd
    runs exactly as declared (the pre-v1.11 behaviour).
    """
    op = resolve(st["out"])
    if graph.kind(st) == "cmd":
        cmd = st["cmd"]
        if st.get("mutates") and not allow_mutations:
            return False, ("step is marked mutates:true (modifies the environment); re-run with "
                           "--allow-mutations after human review ｜ 會改動環境，人工確認後加 --allow-mutations 重跑. "
                           "cmd: " + cmd_display(cmd))
        if isinstance(cmd, list):
            argv = [substitute(str(c), inp, run) if run else str(c) for c in cmd]
            r = subprocess.run(argv, capture_output=True, text=True)
        else:
            line = substitute(cmd, inp, run, quote=True) if run else cmd
            r = subprocess.run(line, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            safe_print(f"  [WARN] cmd exited {r.returncode} — attach a cmd_gate to enforce exit==0 ｜ 加 cmd_gate 強制 exit==0")
        kit.write_artifact(kit.artifact("cmd@1", "cmd",
                           {"command": st["cmd"], "exit": r.returncode,
                            "stdout": (r.stdout or "")[-4000:], "stderr": (r.stderr or "")[-4000:]}), op)
        return True, ""
    tool, ip = kit.kit_path(st["tool"]), resolve(st["in"])
    if graph.kind(st) == "map":
        return run_map(st, tool, ip, op)
    r = subprocess.run([sys.executable, tool, "--in", ip, "--out", op], capture_output=True, text=True)
    ok = (r.returncode == 0) and os.path.exists(op)
    return ok, (r.stderr or r.stdout or "").strip()


def print_plan(flow, stall_window=None):
    """List every operation without executing; statically validate the whole topology.
    Returns an exit code: 0 = clean, 2 = structural problem(s) found.

    The verdict comes from graph.analyze() — the single authority on topology legality, so
    --plan and the runtime cannot disagree about what is legal. This function only renders.
    """
    problems, info = graph.analyze(flow)
    steps = flow["steps"]
    safe_print(f"PLAN flow={flow['name']} (dry run — nothing executed)")
    if stall_window is not None:
        cond = (f"stall after {stall_window} idle round(s) or an A→B→A thrash"
                if stall_window > 0 else "stall disabled (budget-only)")
        safe_print(f"  early-stop: {cond}; budget ceiling is separate")
    for i, st in enumerate(steps):
        n = i + 1
        k = graph.kind(st)
        if k == "branch":
            safe_print(f"  {n}. branch (reads {st['branch']}):")
            for c in st.get("cases", []):
                goto = c.get("goto")
                cond = "default" if c.get("default") else f"when {c.get('when')}"
                disp = goto if goto is not None else "(missing 'goto')"
                bk = f"  [back-edge · max_revisits={c.get('max_revisits')}]" if c.get("back") else ""
                safe_print(f"       {cond} → {disp}{bk}")
        elif k == "cmd":
            mut = "  [MUTATES — needs --allow-mutations]" if st.get("mutates") else ""
            safe_print(f"  {n}. cmd: {cmd_display(st['cmd'])}{mut}")
        elif k in ("tool", "map"):
            mp = f"  [map_over={st['map_over']!r} · per-item]" if k == "map" else ""
            safe_print(f"  {n}. tool: {st['tool']}{mp}")
        else:
            safe_print(f"  {n}.  ✗ malformed (no tool/cmd/branch)")
        node = info["nodes"][i]
        if node["schema_ref"]:
            safe_print(f"       emits: {node['schema_ref']}")
        if node["reads"] or node["writes"]:
            safe_print(f"       state: reads={node['reads'] or '-'} writes={node['writes'] or '-'}")
        if st.get("gate"):
            safe_print(f"       gate: {st['gate']['type']}")
    if info["owners"]:
        safe_print("  state field owners (unique writer per field):")
        for f, owner in sorted(info["owners"].items()):
            safe_print(f"    {f} ← {owner}")
    if problems:
        safe_print("  ⚠️ structural problems:")
        for p in problems:
            safe_print(f"    - {p}")
        return 2
    return 0
