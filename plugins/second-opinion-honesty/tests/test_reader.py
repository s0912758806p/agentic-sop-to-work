# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.reader.read_full.

Builds a synthetic kit-shaped run_dir in a temp dir and asserts the reader pools the
trace, harvests claims/aggregates/verdicts under the recognized convention, and that
the deterministic checks then fire on all three vectors. Prose (a conclusion sentence)
must NOT become a claim — that is the advisory #4 layer's job.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import reader, checks  # noqa: E402


def _make_run(tmp, rel_paths=False):
    art = {
        "schema": "qc@1", "produced_by": "qc",
        "data": {
            "batch_no": "AC-2407-X19",
            "product": "Acetaminophen Tablets 500mg",
            "results": [
                {"test": "Assay", "value": 96.5, "limit_lo": 98.0, "limit_hi": 102.0, "verdict": "PASS"},
                {"test": "Moisture", "value": 0.7, "limit_hi": 5.0, "verdict": "PASS"},
            ],
            "aggregates": [
                {"label": "Total impurities", "op": "sum", "over": [0.30, 0.45, 0.20], "stated": 1.10},
            ],
            "conclusion": "Stable through 24 months.",
        },
        "trace": [
            {"value": "96.5", "source": "coa.pdf", "locator": "line 3"},
            {"value": "0.3", "source": "coa.pdf", "locator": "line 4"},
            {"value": "0.30"}, {"value": "0.45"}, {"value": "0.20"},
            {"value": "98.0"}, {"value": "102.0"}, {"value": "5.0"},
        ],
    }
    apath = os.path.join(tmp, "qc.json")
    with open(apath, "w", encoding="utf-8") as f:
        json.dump(art, f)
    rpath = os.path.join(tmp, "report.md")
    with open(rpath, "w", encoding="utf-8") as f:
        f.write("# QC — DRAFT\nAssay 96.5% PASS\nMoisture 0.7% PASS\n"
                "Total impurities 1.10%\nStable through 24 months.\n")
    out_ref = "qc.json" if rel_paths else apath
    final_ref = "report.md" if rel_paths else rpath
    mani = {"flow": "qc", "run_id": "run_test", "state": "OK_FOR_REVIEW",
            "steps": [{"skill": "qc", "ok": True, "out": out_ref, "error": ""}],
            "final_output": final_ref, "human_review_required": True, "banner": "DRAFT"}
    with open(os.path.join(tmp, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(mani, f)


class TestReadFull(unittest.TestCase):
    def test_reads_pools_harvests_and_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_run(tmp)
            d = reader.read_full(tmp)

            self.assertEqual(d.mode, "FULL")
            self.assertEqual(d.run_id, "run_test")
            self.assertGreaterEqual(len(d.sources), 5)
            self.assertEqual(len(d.aggregates), 1)
            self.assertEqual(len(d.verdicts), 2)

            batch = [c for c in d.claims if c.value == "AC-2407-X19"]
            self.assertEqual(len(batch), 1)
            self.assertFalse(batch[0].sourced)
            self.assertEqual(batch[0].kind, "identifier")

            moist = [c for c in d.claims if c.value == 0.7]
            self.assertTrue(moist)
            self.assertFalse(moist[0].sourced)

            # prose conclusion is NOT harvested as a claim
            self.assertFalse(any("Stable" in str(c.value) for c in d.claims))

            findings = checks.run_checks(d)
            self.assertEqual(sorted({x.vector for x in findings}), ["#1", "#2", "#3"])
            # two #1s: the wrong Assay verdict AND the impurities-sum mismatch
            self.assertGreaterEqual(len([x for x in findings if x.vector == "#1"]), 2)

    def test_resolves_relative_artifact_paths(self):
        # A shipped fixture / relocated run uses bare filenames, not absolute paths.
        with tempfile.TemporaryDirectory() as tmp:
            _make_run(tmp, rel_paths=True)
            d = reader.read_full(tmp)
            self.assertGreaterEqual(len(d.sources), 5)
            self.assertEqual(len(d.verdicts), 2)


if __name__ == "__main__":
    unittest.main()
