# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Integration: code-enforced fix-loop ceiling (--max-fix-retries) + machine-readable failure block.

The fixing itself is Claude-layer (in /sop-flow); here we only verify the deterministic guarantees:
  - run.py emits a structured `failure{step,gate_type,message,artifact}` on a gate failure;
  - re-invoking with the SAME --run-id is capped at 1 + N executions, then refused (`fix_exhausted`).
"""
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


def _failing_flow(d):
    """A tool emitting {data:{id:1}} + schema_gate requiring 'name' → deterministic gate failure."""
    tool = os.path.join(d, "emit.py")
    with open(tool, "w", encoding="utf-8") as f:
        f.write('import json,argparse\n'
                'a=argparse.ArgumentParser();a.add_argument("--in");a.add_argument("--out");x=a.parse_args()\n'
                'json.dump({"schema":"t@1","produced_by":"emit","data":{"id":1},"trace":[]},open(x.out,"w"))\n')
    return _write(d, "flow.json", {
        "name": "always-fails", "input_default": tool,
        "steps": [{"skill": "emit", "tool": tool, "in": "$INPUT", "out": "$RUN/a.json",
                   "gate": {"type": "schema_gate", "args": {"required": ["id", "name"]}}}]})


def _run(flow, runs, run_id, *extra):
    return subprocess.run(
        [sys.executable, RUN, "--flow", flow, "--out-base", runs, "--run-id", run_id, *extra],
        capture_output=True, text=True)


class FixLoopCeiling(unittest.TestCase):
    def test_failure_block_shape(self):
        with tempfile.TemporaryDirectory() as d:
            flow = _failing_flow(d)
            r = _run(flow, os.path.join(d, "runs"), "one", "--max-fix-retries", "3")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            m = json.load(open(os.path.join(d, "runs", "one", "run_manifest.json"), encoding="utf-8"))
            self.assertEqual(m["state"], "FAILED")
            for key in ("step", "gate_type", "message", "artifact"):
                self.assertIn(key, m["failure"])
            self.assertEqual(m["failure"]["gate_type"], "schema_gate")
            self.assertIn("name", m["failure"]["message"])

    def test_cap_refuses_after_N_retries(self):
        with tempfile.TemporaryDirectory() as d:
            flow = _failing_flow(d)
            runs, rid = os.path.join(d, "runs"), "fixed"
            man = os.path.join(runs, rid, "run_manifest.json")
            # N=3 → original + 3 retries = 4 executions allowed; each still runs & FAILs (not exhausted).
            for k in range(4):
                r = _run(flow, runs, rid, "--max-fix-retries", "3")
                self.assertEqual(r.returncode, 2, f"exec {k + 1}: {r.stdout}{r.stderr}")
                m = json.load(open(man, encoding="utf-8"))
                self.assertEqual(m["state"], "FAILED")
                self.assertNotIn("fix_exhausted", m, f"exec {k + 1} must not be exhausted yet")
            # 5th execution → code-enforced refusal (does not run the flow).
            r = _run(flow, runs, rid, "--max-fix-retries", "3")
            self.assertEqual(r.returncode, 2)
            m = json.load(open(man, encoding="utf-8"))
            self.assertTrue(m.get("fix_exhausted"), m)
            self.assertEqual(m.get("max_fix_retries"), 3)

    def test_fresh_run_id_not_capped(self):
        """Different run-ids each have their own counter — normal (non-loop) usage is unaffected."""
        with tempfile.TemporaryDirectory() as d:
            flow = _failing_flow(d)
            runs = os.path.join(d, "runs")
            for rid in ("r1", "r2", "r3"):
                r = _run(flow, runs, rid, "--max-fix-retries", "3")
                self.assertEqual(r.returncode, 2)
                m = json.load(open(os.path.join(runs, rid, "run_manifest.json"), encoding="utf-8"))
                self.assertNotIn("fix_exhausted", m)


if __name__ == "__main__":
    unittest.main()
