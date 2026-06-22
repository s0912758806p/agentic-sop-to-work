# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Unit tests for the bounded-state retention policy (Loop Engineering cut #3).
(run.py --prune integration tests are appended in Task 2.)"""
import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
