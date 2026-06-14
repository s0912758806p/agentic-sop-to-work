# SPDX-License-Identifier: MIT
"""End-to-end (zero-LLM) integration test over the shipped pharma FULL fixture.

The fixture seeds four defects; three are deterministic (the 4th, conclusion overreach,
is the advisory LLM layer's job and is not expected here):
  #1  Assay 96.5% judged PASS (limit 98.0–102.0)  -> wrong verdict
  #1  Total impurities stated 0.40 vs items 0.12+0.08+0.05 = 0.25  -> recompute mismatch
  #2  Moisture 0.7% with no matching trace token (nearest 0.3)  -> fabrication/transcription
  #3  batch_no 'AC-2407-X19' with no provenance  -> should be 【待補】
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import checks, reader, review  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "secondop", "examples", "pharma_stability")


class TestPharmaFull(unittest.TestCase):
    def test_catches_all_deterministic_defects(self):
        d = reader.read_full(FIX)
        findings = checks.run_checks(d)
        by = {}
        for x in findings:
            by.setdefault(x.vector, []).append(x)

        self.assertEqual(sorted(by), ["#1", "#2", "#3"])
        self.assertEqual(len(by["#1"]), 2)   # wrong assay verdict + impurities-sum mismatch
        self.assertEqual(len(by["#2"]), 1)
        self.assertIn("0.3", by["#2"][0].evidence)   # nearest-token transcription hint
        self.assertEqual(len(by["#3"]), 1)
        self.assertIn("AC-2407-X19", by["#3"][0].claim)
        self.assertIn("待補", by["#3"][0].evidence)
        self.assertTrue(all(x.severity == "HARD" for x in findings))
        self.assertTrue(all(x.mode_confidence == 1.0 for x in findings))

    def test_review_run_full_writes_advisory_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            rep, jpath, mpath = review.run_full(FIX, out_base=tmp)
            self.assertEqual(rep["verdict"], "ADVISORY_ONLY")
            self.assertIs(rep["human_owns_verdict"], True)
            self.assertEqual(rep["summary"]["hard"], 4)
            self.assertEqual(rep["summary"]["soft"], 0)
            self.assertTrue(os.path.exists(jpath))
            self.assertTrue(os.path.exists(mpath))


if __name__ == "__main__":
    unittest.main()
