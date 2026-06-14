# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.report.

The report must be structurally incapable of saying "Second Opinion approved this":
verdict is the frozen literal ADVISORY_ONLY and human_owns_verdict is always True.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import report  # noqa: E402
from secondop.model import Finding, NormalizedDraft  # noqa: E402


def _findings():
    return [
        Finding(id="#1:a", vector="#1", severity="HARD", origin="deterministic",
                location="results[0]", claim="verdict 'PASS'", evidence="expected fail",
                mode_confidence=1.0, settled_key="slot:a"),
        Finding(id="#4:b", vector="#4", severity="SOFT", origin="advisory",
                location="conclusion", claim="stable through 24 months",
                evidence="no 24M timepoint", mode_confidence=0.5),
    ]


class TestBuild(unittest.TestCase):
    def test_verdict_is_frozen_advisory_only(self):
        rep = report.build(NormalizedDraft(mode="FULL", run_id="r1", produced_by="qc"), _findings())
        self.assertEqual(rep["verdict"], "ADVISORY_ONLY")
        self.assertIs(rep["human_owns_verdict"], True)

    def test_summary_counts(self):
        rep = report.build(NormalizedDraft(mode="FULL"), _findings())
        s = rep["summary"]
        self.assertEqual(s["hard"], 1)
        self.assertEqual(s["soft"], 1)
        self.assertEqual(s["deterministic"], 1)
        self.assertEqual(s["advisory"], 1)
        self.assertEqual(s["by_vector"]["#1"], 1)
        self.assertEqual(s["by_vector"]["#4"], 1)

    def test_deterministic_findings_listed_before_advisory(self):
        rep = report.build(NormalizedDraft(mode="FULL"), _findings())
        origins = [f["origin"] for f in rep["findings"]]
        self.assertEqual(origins, ["deterministic", "advisory"])


class TestMarkdown(unittest.TestCase):
    def test_has_banner_and_human_owns(self):
        md = report.to_markdown(report.build(NormalizedDraft(mode="FULL"), _findings()))
        self.assertIn("DRAFT", md)
        self.assertIn("ADVISORY", md.upper())
        self.assertIn("Human", md)

    def test_empty_findings_clean_state(self):
        md = report.to_markdown(report.build(NormalizedDraft(mode="FULL"), []))
        self.assertIn("No hard", md)


if __name__ == "__main__":
    unittest.main()
