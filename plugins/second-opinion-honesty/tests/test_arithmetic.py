# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.arithmetic — the deterministic HARD core.

recompute mirrors the kit recompute_gate discipline (count = exact int; sum/mean =
tolerant isclose; non-numeric stated/items never raise). reeval_verdict re-derives a
PASS/FAIL against spec limits and reports what the verdict SHOULD have been.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import arithmetic  # noqa: E402


class TestRecompute(unittest.TestCase):
    def test_count_matches(self):
        ok, derived, _ = arithmetic.recompute("count", [1, 2, 3], 3)
        self.assertTrue(ok)
        self.assertEqual(derived, 3)

    def test_count_mismatch_reports_derived(self):
        ok, derived, reason = arithmetic.recompute("count", [1, 2, 3], 5)
        self.assertFalse(ok)
        self.assertEqual(derived, 3)
        self.assertIn("3", reason)

    def test_sum_tolerant_match(self):
        ok, derived, _ = arithmetic.recompute("sum", [0.1, 0.2], 0.3)
        self.assertTrue(ok)  # float representation must not cause a false mismatch

    def test_sum_mismatch_reports_real_sum(self):
        ok, derived, _ = arithmetic.recompute("sum", [0.30, 0.45, 0.20], 1.10)
        self.assertFalse(ok)
        self.assertAlmostEqual(derived, 0.95)

    def test_mean(self):
        ok, derived, _ = arithmetic.recompute("mean", [2, 4], 3)
        self.assertTrue(ok)
        self.assertAlmostEqual(derived, 3.0)

    def test_nonnumeric_stated_not_ok_never_raises(self):
        ok, _, reason = arithmetic.recompute("sum", [1, 2], "abc")
        self.assertFalse(ok)

    def test_nonnumeric_item_fails_gracefully(self):
        ok, _, _ = arithmetic.recompute("sum", [1, "x"], 1)
        self.assertFalse(ok)  # must not raise

    def test_count_allows_nonnumeric_items(self):
        ok, derived, _ = arithmetic.recompute("count", ["a", "b"], 2)
        self.assertTrue(ok)
        self.assertEqual(derived, 2)


class TestReevalVerdict(unittest.TestCase):
    def test_below_lower_limit_should_be_fail(self):
        ok, expected, _ = arithmetic.reeval_verdict(96.5, 98.0, 102.0, "pass")
        self.assertFalse(ok)
        self.assertEqual(expected, "fail")

    def test_in_spec_pass_is_consistent(self):
        ok, expected, _ = arithmetic.reeval_verdict(99.4, 98.0, 102.0, "pass")
        self.assertTrue(ok)
        self.assertEqual(expected, "pass")

    def test_upper_bound_only_nmt_in_spec(self):
        ok, expected, _ = arithmetic.reeval_verdict(0.18, None, 0.2, "pass")
        self.assertTrue(ok)
        self.assertEqual(expected, "pass")

    def test_upper_bound_exceeded(self):
        ok, expected, _ = arithmetic.reeval_verdict(0.25, None, 0.2, "pass")
        self.assertFalse(ok)
        self.assertEqual(expected, "fail")

    def test_open_bounds_always_in_spec(self):
        ok, expected, _ = arithmetic.reeval_verdict(123.0, None, None, "pass")
        self.assertTrue(ok)
        self.assertEqual(expected, "pass")

    def test_stated_fail_when_actually_in_spec(self):
        ok, expected, _ = arithmetic.reeval_verdict(99.4, 98.0, 102.0, "fail")
        self.assertFalse(ok)
        self.assertEqual(expected, "pass")


if __name__ == "__main__":
    unittest.main()
