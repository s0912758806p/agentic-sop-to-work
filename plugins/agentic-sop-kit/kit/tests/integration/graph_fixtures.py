# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Shared fixtures for the bounded-back-edge integration tests (not a test file itself).

Three tool shapes, because a bounded back-edge has three distinct outcomes and each needs
a tool that genuinely produces it — the kit's dual-termination doctrine
(`budget + stall, whichever fires first`, kit/SOP.md) applies per-edge here:

  improving  -> the loop converges and the flow accepts        (test_graph_flow)
  churning   -> output changes every visit but never passes;
                the declared max_revisits is what stops it     (test_revisit_bound)
  frozen     -> output identical every visit, so the progress
                sensor calls it idle BEFORE the bound is hit   (test_backedge_stall)
"""
import json
import os
import subprocess
import sys

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")

_HEAD = ('import json,argparse,os\n'
         'a=argparse.ArgumentParser();a.add_argument("--in",dest="inp");a.add_argument("--out")\n'
         'x=a.parse_args()\n')

# Visit counter lives beside the tool's own output, so it is run-scoped like everything else.
_COUNT = ('c=os.path.join(os.path.dirname(x.out),".visits")\n'
          'n=(int(open(c).read()) if os.path.exists(c) else 0)+1\n'
          'open(c,"w").write(str(n))\n')


def _write(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return p


def _tool(d, name, body):
    p = os.path.join(d, name + ".py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(_HEAD + body)
    return p


def improving_tool(d):
    """defects shrinks each visit: visit 1 -> 1 (reject), visit 2 -> 0 (pass)."""
    return _tool(d, "revise", _COUNT +
                 'json.dump({"schema":"draft@1","produced_by":"revise",\n'
                 '  "data":{"attempt":n,"defects":max(0,2-n)},"trace":[]},open(x.out,"w"))\n')


def churning_tool(d):
    """Never passes, but the artifact really does change every visit (attempt increments),
    so the progress sensor sees progress and only the declared bound can stop the loop."""
    return _tool(d, "churn", _COUNT +
                 'json.dump({"schema":"draft@1","produced_by":"churn",\n'
                 '  "data":{"attempt":n,"defects":1},"trace":[]},open(x.out,"w"))\n')


def frozen_tool(d):
    """Byte-identical output every visit — genuine no-progress, which is what `idle` means."""
    return _tool(d, "frozen", 'json.dump({"schema":"draft@1","produced_by":"frozen",\n'
                              '  "data":{"attempt":1,"defects":1},"trace":[]},open(x.out,"w"))\n')


def _review_tool(d):
    """Deterministic router: the verdict is derived from the upstream artifact, never from a
    model. `attempt` is passed through so the routing state reflects real change upstream."""
    return _tool(d, "review",
                 'up=json.load(open(x.inp))\n'
                 'v="reject" if up["data"]["defects"]>0 else "pass"\n'
                 'json.dump({"schema":"verdict@1","produced_by":"review",\n'
                 '  "data":{"verdict":v,"defects":up["data"]["defects"],\n'
                 '          "attempt":up["data"]["attempt"]},"trace":[]},open(x.out,"w"))\n')


def _accept_tool(d):
    return _tool(d, "accept",
                 'json.dump({"schema":"accepted@1","produced_by":"accept",\n'
                 '  "data":{"ok":True},"trace":[]},open(x.out,"w"))\n')


def graph_flow(d, body_tool, max_revisits=2):
    """revise → review → gate ──reject (bounded back-edge)──▶ revise
                                └─default──▶ accept

    The four-node shape of the graph-engineering picture, domain-neutral and dep-free.
    """
    return _write(d, "flow.json", {
        "name": "graph-demo", "input_default": body_tool,
        "steps": [
            {"skill": "revise", "tool": body_tool, "in": "$INPUT", "out": "$RUN/draft.json",
             "writes": ["draft"]},
            {"skill": "review", "tool": _review_tool(d), "in": "$RUN/draft.json",
             "out": "$RUN/verdict.json", "reads": ["draft"], "writes": ["verdict"]},
            {"id": "gate", "branch": "$RUN/verdict.json", "cases": [
                {"when": {"path": "verdict", "op": "==", "value": "reject"},
                 "goto": "revise", "back": True, "max_revisits": max_revisits},
                {"default": True, "goto": "accept"}]},
            {"skill": "accept", "tool": _accept_tool(d), "in": "$RUN/verdict.json",
             "out": "$RUN/accepted.json", "reads": ["verdict"]},
        ]})


def run_flow(flow, base, run_id="g", *extra):
    return subprocess.run([sys.executable, RUN, "--flow", flow, "--out-base", base,
                           "--run-id", run_id, *extra], capture_output=True, text=True)


def manifest(base, run_id="g"):
    with open(os.path.join(base, run_id, "run_manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def nodes_walked(mani):
    return [p["node"] for p in mani.get("path_taken", [])]
