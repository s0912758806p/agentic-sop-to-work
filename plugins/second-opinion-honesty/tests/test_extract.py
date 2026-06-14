# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.extract (DEGRADED-mode best-effort extraction).

DEGRADED mode has no kit trace, so we tokenize user-supplied inputs into a best-effort
allow-set and scan the plain document for numeric + identifier claims. #1 (verdicts/
aggregates) is largely unavailable from prose and is left to the advisory LLM layer; the
deterministic value here is #2/#3, downgraded to SOFT.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import extract  # noqa: E402


class TestExtractSources(unittest.TestCase):
    def test_tokenizes_numbers_and_ids_from_text(self):
        text = "assay 96.5\nmoisture 0.3\nbatch AC-2407-X19\n"
        srcs = extract.extract_sources_from_text(text, "inputs.txt")
        vals = {s["value"] for s in srcs}
        self.assertIn("96.5", vals)
        self.assertIn("0.3", vals)
        self.assertIn("AC-2407-X19", vals)
        self.assertTrue(all(s["source"] == "inputs.txt" for s in srcs))

    def test_locator_is_line_number(self):
        srcs = extract.extract_sources_from_text("a 1\nb 2\n", "x")
        two = [s for s in srcs if s["value"] == "2"][0]
        self.assertIn("2", two["locator"])  # "line 2"


class TestExtractClaims(unittest.TestCase):
    SOURCES = [{"value": "96.5"}, {"value": "0.3"}]

    def test_number_claim_sourced_flag(self):
        claims = extract.extract_claims("Assay: 96.5%\nMoisture: 0.7%\n", self.SOURCES)
        by = {round(c.value, 4) if isinstance(c.value, float) else c.value: c for c in claims}
        self.assertIn(96.5, by)
        self.assertTrue(by[96.5].sourced)        # 96.5 is in sources
        self.assertIn(0.7, by)
        self.assertFalse(by[0.7].sourced)        # 0.7 is not -> SOFT fabrication later

    def test_placeholder_detected(self):
        claims = extract.extract_claims("Lot: 【待補】\n", self.SOURCES)
        self.assertTrue(any(c.kind == "placeholder" for c in claims))

    def test_identifier_claim(self):
        claims = extract.extract_claims("Batch AC-2407-X19 released\n", self.SOURCES)
        ids = [c for c in claims if c.kind == "identifier"]
        self.assertTrue(any("AC-2407-X19" in str(c.value) for c in ids))

    def test_prose_without_numbers_yields_no_numeric_claim(self):
        claims = extract.extract_claims("The product appears stable overall.\n", self.SOURCES)
        self.assertFalse(any(c.kind == "number" for c in claims))


if __name__ == "__main__":
    unittest.main()
