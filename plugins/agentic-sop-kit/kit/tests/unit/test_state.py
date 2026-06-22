# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Unit tests for the bounded-state retention policy (Loop Engineering cut #3).
(run.py --prune integration tests are appended in Task 2.)"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RUN = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "workflow", "run.py")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "lib"))
from loop import state  # noqa: E402


class LogKeep(unittest.TestCase):
    def test_floor_enforced(self):
        self.assertEqual(state.log_keep_count(10, 50), 50)    # below floor → floor
        self.assertEqual(state.log_keep_count(200, 50), 200)  # above floor → as-is

    def test_default_is_200(self):
        self.assertEqual(state.log_keep_count(), 200)


class RunsEvict(unittest.TestCase):
    def test_under_keep_is_empty(self):
        entries = [("r%d" % i, float(i)) for i in range(5)]
        self.assertEqual(state.runs_to_evict(entries, keep_runs=20), [])

    def test_evicts_oldest_beyond_keep(self):
        entries = [("r%02d" % i, float(i)) for i in range(25)]  # r00 oldest .. r24 newest
        evicted = state.runs_to_evict(entries, keep_runs=20)
        self.assertEqual(sorted(evicted), ["r00", "r01", "r02", "r03", "r04"])  # 5 oldest

    def test_tiebreak_deterministic(self):
        entries = [("b", 1.0), ("a", 1.0), ("c", 1.0)]  # identical mtime
        # newest by (mtime, run_id) desc = "c"; keep 1 → evict a, b
        self.assertEqual(sorted(state.runs_to_evict(entries, keep_runs=1)), ["a", "b"])


class PruneCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.base = os.path.join(self.tmp, "runs")
        os.makedirs(self.base)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mkruns(self, n):
        for i in range(n):
            d = os.path.join(self.base, "run_%02d" % i)
            os.makedirs(d)
            os.utime(d, (1000 + i, 1000 + i))  # ascending mtime → run_00 oldest, run_(n-1) newest

    def _run(self, *args):
        return subprocess.run([sys.executable, RUN, "--out-base", self.base, *args],
                              capture_output=True, text=True)

    def test_prune_evicts_beyond_keep(self):
        self._mkruns(25)
        r = self._run("--prune")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        left = sorted(os.listdir(self.base))
        self.assertEqual(len(left), 20)
        self.assertNotIn("run_00", left)  # oldest evicted
        self.assertIn("run_24", left)     # newest kept

    def test_prune_under_keep_is_noop(self):
        self._mkruns(10)
        self.assertEqual(self._run("--prune").returncode, 0)
        self.assertEqual(len(os.listdir(self.base)), 10)

    def test_advisory_prints_when_over_limit(self):
        self._mkruns(21)
        r = self._run("--plan")  # advisory prints in --plan mode too; no flow is executed
        self.assertIn("prunable", r.stdout.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
