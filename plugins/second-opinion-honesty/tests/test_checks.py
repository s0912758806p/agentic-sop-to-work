# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.checks — the three deterministic honesty checks.

Scheme (disjoint, one finding per unsourced slot):
  #1 check_arith_verdict   wrong PASS/FAIL vs spec limits + aggregate recompute mismatch
  #2 check_fabrication     unsourced NUMERIC values (nearest-token transcription hint)
  #3 check_missing_source  unsourced NON-NUMERIC values (id/date/name) -> should be 【待補】
Severity: HARD@1.0 in FULL mode, SOFT@0.5 in DEGRADED mode.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import checks  # noqa: E402
from secondop.model import NormalizedDraft, Claim, Aggregate, Verdict  # noqa: E402

# Realistic trace (matches the kit demo); nearest token to 0.7 is unambiguously 0.3.
SRC = [{"value": "99.4", "source": "r.pdf", "locator": "line 2"},
       {"value": "0.3", "source": "r.pdf", "locator": "line 5"},
       {"value": "7.1"}, {"value": "250"}, {"value": "0.12"}]


class TestArithVerdict(unittest.TestCase):  # vector #1
    def test_wrong_pass_flagged_hard_in_full(self):
        d = NormalizedDraft(mode="FULL", verdicts=[
            Verdict(id="assay", text="PASS", polarity="pass", measured=96.5,
                    lo=98.0, hi=102.0, locator="report:assay")])
        f = checks.check_arith_verdict(d)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].vector, "#1")
        self.assertEqual(f[0].severity, "HARD")
        self.assertEqual(f[0].mode_confidence, 1.0)

    def test_correct_verdict_no_finding(self):
        d = NormalizedDraft(mode="FULL", verdicts=[
            Verdict(id="assay", text="PASS", polarity="pass", measured=99.4, lo=98.0, hi=102.0)])
        self.assertEqual(checks.check_arith_verdict(d), [])

    def test_aggregate_sum_mismatch_flagged(self):
        d = NormalizedDraft(mode="FULL", aggregates=[
            Aggregate(id="imp", op="sum", over=[0.30, 0.45, 0.20], stated=1.10,
                      stated_locator="report:imp")])
        f = checks.check_arith_verdict(d)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].vector, "#1")
        self.assertIn("0.95", f[0].evidence)

    def test_verdict_without_limits_skipped(self):
        d = NormalizedDraft(mode="FULL", verdicts=[
            Verdict(id="x", text="PASS", polarity="pass", measured=5.0, lo=None, hi=None)])
        self.assertEqual(checks.check_arith_verdict(d), [])

    def test_degraded_is_soft(self):
        d = NormalizedDraft(mode="DEGRADED", aggregates=[
            Aggregate(id="imp", op="sum", over=[0.3, 0.45, 0.2], stated=1.10)])
        f = checks.check_arith_verdict(d)
        self.assertEqual(f[0].severity, "SOFT")
        self.assertEqual(f[0].mode_confidence, 0.5)


class TestFabrication(unittest.TestCase):  # vector #2 (numeric, unsourced)
    def test_unsourced_number_flagged_with_nearest(self):
        d = NormalizedDraft(mode="FULL", sources=SRC, claims=[
            Claim(id="moist", value=0.7, label="moisture", location="report:moist", sourced=False)])
        f = checks.check_fabrication(d)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].vector, "#2")
        self.assertIn("0.3", f[0].evidence)  # nearest-token transcription hint

    def test_sourced_number_not_flagged(self):
        d = NormalizedDraft(mode="FULL", sources=SRC, claims=[
            Claim(id="a", value=99.4, sourced=True)])
        self.assertEqual(checks.check_fabrication(d), [])

    def test_nonnumeric_not_in_fabrication(self):
        d = NormalizedDraft(mode="FULL", sources=SRC, claims=[
            Claim(id="batch", value="B-2407-X", sourced=False)])
        self.assertEqual(checks.check_fabrication(d), [])  # strings are #3's job


class TestMissingSource(unittest.TestCase):  # vector #3 (non-numeric, unsourced)
    def test_unsourced_identifier_flagged(self):
        d = NormalizedDraft(mode="FULL", sources=SRC, claims=[
            Claim(id="batch", value="B-2407-X", label="batch no",
                  location="report:batch", sourced=False)])
        f = checks.check_missing_source(d)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].vector, "#3")
        self.assertIn("待補", f[0].evidence)

    def test_placeholder_not_flagged(self):
        d = NormalizedDraft(mode="FULL", sources=SRC, claims=[
            Claim(id="x", value="【待補】", kind="placeholder", sourced=False)])
        self.assertEqual(checks.check_missing_source(d), [])

    def test_numeric_not_in_missing_source(self):
        d = NormalizedDraft(mode="FULL", sources=SRC, claims=[
            Claim(id="m", value=0.7, sourced=False)])
        self.assertEqual(checks.check_missing_source(d), [])  # numbers are #2's job


class TestRunChecks(unittest.TestCase):
    def test_registry_runs_all_three_vectors(self):
        d = NormalizedDraft(
            mode="FULL", sources=SRC,
            verdicts=[Verdict(id="assay", text="PASS", polarity="pass",
                              measured=96.5, lo=98.0, hi=102.0)],
            claims=[Claim(id="batch", value="B-2407-X", sourced=False),
                    Claim(id="moist", value=0.7, sourced=False)])
        f = checks.run_checks(d)
        self.assertEqual(sorted({x.vector for x in f}), ["#1", "#2", "#3"])
        self.assertTrue(all(x.origin == "deterministic" for x in f))


if __name__ == "__main__":
    unittest.main()
