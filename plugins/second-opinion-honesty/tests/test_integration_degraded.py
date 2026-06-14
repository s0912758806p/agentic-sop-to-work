# SPDX-License-Identifier: MIT
"""End-to-end DEGRADED-mode test (no kit trace; user supplies inputs).

The SAME logical defects as the FULL fixture, but with no trace: findings degrade to
SOFT @ 0.5, #1 (verdict/aggregate precision) is not available deterministically, and the
unsourced moisture value and fabricated batch number are still surfaced for the human.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import checks, reader, review  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "secondop", "examples", "plain_doc")
DOC = os.path.join(FIX, "report.md")
INPUTS = [os.path.join(FIX, "inputs.txt")]


class TestPlainDocDegraded(unittest.TestCase):
    def test_degraded_findings_are_soft(self):
        d = reader.read_degraded(DOC, INPUTS)
        self.assertEqual(d.mode, "DEGRADED")
        findings = checks.run_checks(d)
        self.assertTrue(findings)  # something surfaced
        self.assertTrue(all(f.severity == "SOFT" for f in findings))
        self.assertTrue(all(f.mode_confidence == 0.5 for f in findings))

        vectors = {f.vector for f in findings}
        self.assertIn("#2", vectors)   # unsourced numbers (moisture 0.7, ...)
        self.assertIn("#3", vectors)   # fabricated batch identifier
        self.assertFalse(any(f.severity == "HARD" for f in findings))

        moisture = [f for f in findings if f.vector == "#2" and "0.7" in f.claim]
        self.assertTrue(moisture)
        batch = [f for f in findings if f.vector == "#3" and "AC-2407-X19" in f.claim]
        self.assertTrue(batch)

    def test_review_run_degraded_writes_advisory_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            rep, jpath, mpath = review.run_degraded(DOC, INPUTS, out_base=tmp)
            self.assertEqual(rep["verdict"], "ADVISORY_ONLY")
            self.assertEqual(rep["review_of"]["mode"], "DEGRADED")
            self.assertEqual(rep["summary"]["hard"], 0)
            self.assertTrue(os.path.exists(jpath) and os.path.exists(mpath))


if __name__ == "__main__":
    unittest.main()
