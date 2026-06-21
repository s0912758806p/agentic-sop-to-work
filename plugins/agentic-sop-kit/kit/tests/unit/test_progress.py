# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Unit tests for the deterministic loop-progress signal (stall detection cut #1)."""
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "lib"))
from loop import progress  # noqa: E402


class Signature(unittest.TestCase):
    def test_same_failure_same_signature(self):
        f = {"step": "emit", "gate_type": "schema_gate", "message": "missing required: name"}
        self.assertEqual(progress.progress_signature(f), progress.progress_signature(f))

    def test_artifact_excluded(self):
        a = {"step": "emit", "gate_type": "schema_gate", "message": "m", "artifact": "/x/runs/r1/a.json"}
        b = {"step": "emit", "gate_type": "schema_gate", "message": "m", "artifact": "/x/runs/r2/a.json"}
        self.assertEqual(progress.progress_signature(a), progress.progress_signature(b))

    def test_run_dir_stripped(self):
        a = {"step": "cmd: x", "gate_type": None, "message": "wrote /tmp/runs/r1/o.json failed"}
        b = {"step": "cmd: x", "gate_type": None, "message": "wrote /tmp/runs/r2/o.json failed"}
        self.assertEqual(progress.progress_signature(a, run_dir="/tmp/runs/r1"),
                         progress.progress_signature(b, run_dir="/tmp/runs/r2"))

    def test_different_failure_different_signature(self):
        a = {"step": "emit", "gate_type": "schema_gate", "message": "missing required: name"}
        b = {"step": "emit", "gate_type": "schema_gate", "message": "missing required: date"}
        self.assertNotEqual(progress.progress_signature(a), progress.progress_signature(b))


class Classify(unittest.TestCase):
    def test_idle_window_2(self):
        self.assertEqual(progress.classify_progress(["A", "A"], 2), "idle")

    def test_not_idle_when_last_two_differ(self):
        self.assertIsNone(progress.classify_progress(["A", "B"], 2))

    def test_idle_needs_full_window(self):
        self.assertIsNone(progress.classify_progress(["A"], 2))

    def test_thrash_aba(self):
        self.assertEqual(progress.classify_progress(["A", "B", "A"], 2), "thrash")

    def test_all_distinct_is_progress(self):
        self.assertIsNone(progress.classify_progress(["A", "B", "C"], 2))

    def test_len3_cycle_not_caught(self):
        self.assertIsNone(progress.classify_progress(["A", "B", "C", "A"], 2))

    def test_window_zero_disables(self):
        self.assertIsNone(progress.classify_progress(["A", "A", "A"], 0))


if __name__ == "__main__":
    unittest.main()
