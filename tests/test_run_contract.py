# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Run-dir contract test: the WRITER (agentic-sop-kit) and the single READER definition
(`shared/sopcore/run_contract.py`, vendored into every companion) must not drift.

The kit is run for real, as a subprocess and from outside the kit, on its bundled flows;
the resulting run dir is then read with run_contract. The kit is deliberately NOT a
sopcore consumer (it writes the contract, it does not read it) — this test is the binding.

Run: python3 tests/test_run_contract.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared"))
from sopcore import run_contract  # noqa: E402

KIT = os.path.join(ROOT, "plugins", "agentic-sop-kit", "kit")
RUN_PY = os.path.join(KIT, "workflow", "run.py")


def _run_kit(flow, out_base, run_id, *extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, RUN_PY, "--flow", flow, "--out-base", out_base, "--run-id", run_id, *extra],
        cwd=out_base, capture_output=True, text=True, encoding="utf-8", env=env)


class TestRunContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sopcore-contract-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ok(self, flow_rel, rid):
        r = _run_kit(os.path.join(KIT, "workflow", flow_rel), self.tmp, rid)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return run_contract.load(os.path.join(self.tmp, rid))

    def test_linear_flow(self):
        rc = self._ok("flow.json", "linear")
        self.assertEqual((rc.run_id, rc.state), ("linear", run_contract.OK_FOR_REVIEW))
        self.assertEqual([s.skill for s in rc.steps], ["extract", "compute", "report"])
        self.assertEqual([os.path.basename(a.path) for a in rc.json_artifacts()],
                         ["a.readings.json", "b.stats.json"])
        self.assertTrue(rc.pooled_trace(), "kit artifacts carry a trace")
        self.assertEqual(os.path.basename(rc.final_output), "report.md")
        feed = rc.feeding_artifact()   # final is markdown -> the last JSON artifact feeds it
        self.assertEqual(os.path.basename(feed.path), "b.stats.json")
        self.assertEqual(rc.produced_by, feed.produced_by)
        self.assertTrue(feed.produced_by)
        self.assertIsInstance(feed.data, dict)

    def test_graph_flow_skips_branch_entries(self):
        rc = self._ok(os.path.join("examples", "graph.json"), "graph")
        raw = [s["skill"] for s in rc.manifest["steps"]]
        self.assertTrue(any(s.startswith("branch→") for s in raw), "fixture must exercise branches")
        self.assertFalse(any(s.skill.startswith("branch→") for s in rc.steps))
        self.assertEqual(os.path.basename(rc.final_output), "accepted.json")
        # revisits do not duplicate artifacts; the archived visits are not in the contract
        names = [os.path.basename(a.path) for a in rc.json_artifacts()]
        self.assertEqual(names, ["draft.json", "verdict.json", "accepted.json"])
        self.assertEqual(os.path.basename(rc.feeding_artifact().path), "accepted.json")

    def test_relocated_run_dir_still_reads(self):
        self._ok("flow.json", "moved")
        dst = os.path.join(self.tmp, "elsewhere")
        shutil.move(os.path.join(self.tmp, "moved"), dst)
        rc = run_contract.load(dst)   # the manifest's absolute paths are now stale
        self.assertEqual(len(rc.json_artifacts()), 2)
        self.assertTrue(rc.final_output.startswith(dst))

    def test_failed_run_is_refused(self):
        bad = os.path.join(self.tmp, "bad_flow.json")
        with open(bad, "w", encoding="utf-8") as f:
            json.dump({"name": "bad", "input_default": "example/inputs/sample_readings.txt",
                       # mutates:true without --allow-mutations: refused before it executes
                       "steps": [{"cmd": "echo never-run", "mutates": True, "out": "$RUN/x.json"}]}, f)
        r = _run_kit(bad, self.tmp, "failed")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(os.path.join(self.tmp, "failed", run_contract.MANIFEST), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["state"], "FAILED")
        with self.assertRaises(run_contract.RunNotReviewable) as cm:
            run_contract.load(os.path.join(self.tmp, "failed"))
        self.assertIn("FAILED", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
