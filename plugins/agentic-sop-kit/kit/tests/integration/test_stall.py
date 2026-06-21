# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Integration: deterministic stall detection in the fix-loop (Loop Engineering cut #1).

The fixing itself is Claude-layer; here we verify only the deterministic guarantees."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")


def _write(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return p


def _run(flow, runs, run_id, *extra):
    return subprocess.run(
        [sys.executable, RUN, "--flow", flow, "--out-base", runs, "--run-id", run_id, *extra],
        capture_output=True, text=True)


def _idle_flow(d):
    """Static tool: {id:1} + schema_gate requiring name -> identical failure every run."""
    tool = os.path.join(d, "emit.py")
    with open(tool, "w", encoding="utf-8") as f:
        f.write('import json,argparse\n'
                'a=argparse.ArgumentParser();a.add_argument("--in");a.add_argument("--out");x=a.parse_args()\n'
                'json.dump({"schema":"t@1","produced_by":"emit","data":{"id":1},"trace":[]},open(x.out,"w"))\n')
    return _write(d, "flow.json", {
        "name": "idle", "input_default": tool,
        "steps": [{"skill": "emit", "tool": tool, "in": "$INPUT", "out": "$RUN/a.json",
                   "gate": {"type": "schema_gate", "args": {"required": ["id", "name"]}}}]})


def _counting_flow(d, name, body_expr):
    """Tool whose emitted data depends on a per-run-dir counter `.tc` (body_expr -> data dict)."""
    tool = os.path.join(d, name + ".py")
    with open(tool, "w", encoding="utf-8") as f:
        f.write('import json,argparse,os\n'
                'a=argparse.ArgumentParser();a.add_argument("--in");a.add_argument("--out");x=a.parse_args()\n'
                'c=os.path.join(os.path.dirname(x.out),".tc")\n'
                'n=int(open(c).read()) if os.path.exists(c) else 0\n'
                'open(c,"w").write(str(n+1))\n'
                'data=' + body_expr + '\n'
                'json.dump({"schema":"t@1","produced_by":"' + name + '","data":data,"trace":[]},open(x.out,"w"))\n')
    return _write(d, "flow.json", {
        "name": name, "input_default": tool,
        "steps": [{"skill": name, "tool": tool, "in": "$INPUT", "out": "$RUN/a.json",
                   "gate": {"type": "schema_gate", "args": {"required": ["id", "name", "date"]}}}]})


class Stall(unittest.TestCase):
    def test_idle_stalls_before_budget(self):
        with tempfile.TemporaryDirectory() as d:
            flow, runs, rid = _idle_flow(d), os.path.join(d, "runs"), "s1"
            man = os.path.join(runs, rid, "run_manifest.json")
            r1 = _run(flow, runs, rid, "--stall-window", "2", "--max-fix-retries", "5")
            self.assertEqual(r1.returncode, 2, r1.stdout + r1.stderr)
            self.assertNotIn("stalled", json.load(open(man, encoding="utf-8")))
            r2 = _run(flow, runs, rid, "--stall-window", "2", "--max-fix-retries", "5")
            self.assertEqual(r2.returncode, 2)
            m2 = json.load(open(man, encoding="utf-8"))
            self.assertTrue(m2.get("stalled"))
            self.assertEqual(m2.get("stall_reason"), "idle")
            self.assertNotIn("fix_exhausted", m2)  # fired earlier than the budget ceiling

    def test_thrash_stalls(self):
        with tempfile.TemporaryDirectory() as d:
            # alternate which required field is present -> failure alternates date/name -> A,B,A
            flow = _counting_flow(d, "thrash", '{"id":1,"name":"x"} if n%2==0 else {"id":1,"date":"y"}')
            runs, rid = os.path.join(d, "runs"), "s2"
            man = os.path.join(runs, rid, "run_manifest.json")
            for _ in range(3):  # window 3 so idle never fires; thrash (cap 2) catches A->B->A at exec 3
                r = _run(flow, runs, rid, "--stall-window", "3", "--max-fix-retries", "9")
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            m = json.load(open(man, encoding="utf-8"))
            self.assertTrue(m.get("stalled"))
            self.assertEqual(m.get("stall_reason"), "thrash")

    def test_real_fix_completes_no_stall(self):
        with tempfile.TemporaryDirectory() as d:
            # round 1 missing name (fail), round 2 complete (success) -> genuine progress
            flow = _counting_flow(d, "fixme", '{"id":1,"date":"d"} if n==0 else {"id":1,"name":"ok","date":"d"}')
            runs, rid = os.path.join(d, "runs"), "s3"
            man = os.path.join(runs, rid, "run_manifest.json")
            r1 = _run(flow, runs, rid, "--stall-window", "2", "--max-fix-retries", "5")
            self.assertEqual(r1.returncode, 2)
            self.assertNotIn("stalled", json.load(open(man, encoding="utf-8")))
            r2 = _run(flow, runs, rid, "--stall-window", "2", "--max-fix-retries", "5")
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            self.assertEqual(json.load(open(man, encoding="utf-8"))["state"], "OK_FOR_REVIEW")

    def test_stalled_refuses_rerun(self):
        with tempfile.TemporaryDirectory() as d:
            flow, runs, rid = _idle_flow(d), os.path.join(d, "runs"), "s4"
            man = os.path.join(runs, rid, "run_manifest.json")
            for _ in range(2):  # exec 1 + exec 2 -> stalled (idle, window 2)
                _run(flow, runs, rid, "--stall-window", "2", "--max-fix-retries", "5")
            r3 = _run(flow, runs, rid, "--stall-window", "2", "--max-fix-retries", "5")
            self.assertEqual(r3.returncode, 2)
            m = json.load(open(man, encoding="utf-8"))
            self.assertTrue(m.get("stalled"))
            self.assertEqual(m.get("stall_reason"), "already_stalled")


if __name__ == "__main__":
    unittest.main()
