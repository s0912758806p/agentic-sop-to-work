# SPDX-License-Identifier: MIT
"""Domain-neutrality proof: the SAME engine catches defects in pharma, frontend, and
backend DRAFTs — it only reads the artifact contract, never any domain knowledge.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import checks, reader  # noqa: E402

EX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secondop", "examples")


def _vectors(fixture):
    findings = checks.run_checks(reader.read_full(os.path.join(EX, fixture)))
    by = {}
    for f in findings:
        by.setdefault(f.vector, []).append(f)
    return findings, by


class TestCrossDomain(unittest.TestCase):
    def test_every_domain_yields_a_hard_finding(self):
        for fixture in ("pharma_stability", "fe_deploy", "be_api"):
            findings, _ = _vectors(fixture)
            self.assertTrue(any(f.severity == "HARD" for f in findings),
                            f"{fixture} produced no HARD finding")

    def test_frontend_catches_build_lie_and_fabricated_metric(self):
        _, by = _vectors("fe_deploy")
        self.assertIn("#1", by)   # "build green" verdict contradicts exit code 1
        self.assertIn("#2", by)   # fabricated lighthouse score (no trace)

    def test_backend_catches_overreach_count_and_fabricated_id(self):
        _, by = _vectors("be_api")
        self.assertIn("#1", by)   # 8 conform but verdict PASS against limit ≥12
        self.assertIn("#3", by)   # fabricated trace_id (no provenance)


if __name__ == "__main__":
    unittest.main()
