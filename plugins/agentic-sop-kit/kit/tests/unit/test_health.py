# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Unit tests for the deterministic runtime-health reader (Loop Engineering cut #2)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "lib"))
from loop import health  # noqa: E402


def _entry(trigger="all", total=1.0, unit=None, integration=None):
    return {"trigger": trigger, "metrics": {"total_seconds": total},
            "unit": unit or [], "integration": integration or []}


class Coverage(unittest.TestCase):
    def test_first_run_returns_none(self):
        self.assertIsNone(health.check_coverage(17, None))

    def test_no_regression_returns_none(self):
        self.assertIsNone(health.check_coverage(18, 17))
        self.assertIsNone(health.check_coverage(17, 17))

    def test_regression_is_hard_finding(self):
        r = health.check_coverage(16, 17)
        self.assertIsNotNone(r)
        self.assertEqual(r["signal"], "coverage")
        self.assertEqual((r["current"], r["baseline"]), (16, 17))

    def test_count_registered_dedups(self):
        reg = {"skills": {"a": {"tests": ["t/a.py"]}, "b": {"tests": ["t/b.py"]}},
               "integration": {"tests": ["t/i.py", "t/a.py"]}}  # a.py appears twice
        self.assertEqual(health.count_registered_tests(reg), 3)


class Slowdown(unittest.TestCase):
    def test_insufficient_history_returns_none(self):
        self.assertIsNone(health.check_slowdown([_entry(total=1.0)] * 7))  # need recent+base=8

    def test_steady_returns_none(self):
        self.assertIsNone(health.check_slowdown([_entry(total=1.0)] * 8))

    def test_slowdown_flagged(self):
        entries = [_entry(total=1.0)] * 5 + [_entry(total=3.0)] * 3  # base med 1.0, recent med 3.0
        r = health.check_slowdown(entries)
        self.assertIsNotNone(r)
        self.assertEqual(r["signal"], "slowdown")

    def test_change_runs_ignored(self):
        self.assertIsNone(health.check_slowdown([_entry(trigger="change", total=9.0)] * 12))

    def test_zero_baseline_returns_none(self):
        entries = [_entry(total=0.0)] * 5 + [_entry(total=100.0)] * 3
        self.assertIsNone(health.check_slowdown(entries))


class Flaky(unittest.TestCase):
    def test_stable_returns_none(self):
        entries = [_entry(integration=[{"test": "x.py", "passed": True}]) for _ in range(5)]
        self.assertIsNone(health.check_flaky(entries))

    def test_flip_flagged(self):
        entries = [_entry(integration=[{"test": "x.py", "passed": True}]),
                   _entry(integration=[{"test": "x.py", "passed": False}])]
        r = health.check_flaky(entries)
        self.assertIsNotNone(r)
        self.assertEqual(r["tests"], ["x.py"])

    def test_outside_window_ignored(self):
        old_fail = _entry(integration=[{"test": "x.py", "passed": False}])
        recent = [_entry(integration=[{"test": "x.py", "passed": True}]) for _ in range(10)]
        self.assertIsNone(health.check_flaky([old_fail] + recent, window=10))


class Assess(unittest.TestCase):
    def test_hard_and_advisory_split(self):
        reg = {"skills": {}, "integration": {"tests": ["a", "b"]}}  # count 2
        entries = [_entry(integration=[{"test": "x.py", "passed": True}]),
                   _entry(integration=[{"test": "x.py", "passed": False}])]
        rep = health.assess_health(reg, entries, baseline=5)  # 2 < 5 → coverage hard
        self.assertEqual([h["signal"] for h in rep["hard"]], ["coverage"])
        self.assertTrue(any(a["signal"] == "flaky" for a in rep["advisory"]))

    def test_clean_is_empty(self):
        reg = {"skills": {}, "integration": {"tests": ["a", "b"]}}
        self.assertEqual(health.assess_health(reg, [], baseline=2), {"hard": [], "advisory": []})


if __name__ == "__main__":
    unittest.main(verbosity=2)
