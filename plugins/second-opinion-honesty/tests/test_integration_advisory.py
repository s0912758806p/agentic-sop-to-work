# SPDX-License-Identifier: MIT
"""End-to-end test of the advisory fold-in: the deterministic pass writes an envelope,
the LLM proposes candidate findings, and review folds them through the code guardrails
(clamp + evidence gate + settled suppression + pass cap) into the final report.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import review  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "secondop", "examples", "pharma_stability")


class TestAdvisoryFold(unittest.TestCase):
    def test_advisory_findings_clamped_and_gated(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1) deterministic pass writes the envelope for the LLM
            review.run_full(FIX, out_base=tmp)
            out_dir = os.path.join(tmp, "run_demo_pharma_stability")
            self.assertTrue(os.path.exists(os.path.join(out_dir, "llm_input.json")))

            # 2) the LLM proposes one real #4 (quotes the draft) and one uncited junk finding
            candidates = {"findings": [
                {"vector": "#4", "location": "conclusion",
                 "claim": "Stable through 24 months", "evidence": "longest timepoint is 6M; NO SOURCE",
                 "confidence": 0.9},
                {"vector": "#4", "location": "nowhere",
                 "claim": "a completely invented accusation", "evidence": "vibes", "confidence": 0.5},
            ]}
            cpath = os.path.join(tmp, "candidates.json")
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(candidates, f)

            # 3) fold them in
            rep, _, _ = review.run_full(FIX, out_base=tmp, advisory_path=cpath)
            self.assertEqual(rep["summary"]["hard"], 4)       # deterministic unchanged
            self.assertEqual(rep["summary"]["soft"], 1)       # only the cited #4 survives
            self.assertEqual(rep["summary"]["llm_dropped"], 1)  # junk gated out
            adv = [f for f in rep["findings"] if f["origin"] == "advisory"]
            self.assertEqual(len(adv), 1)
            self.assertEqual(adv[0]["severity"], "SOFT")
            self.assertLessEqual(adv[0]["mode_confidence"], 0.5)  # clamped from 0.9
            self.assertEqual(rep["llm"]["passes_used"], 1)

    def test_pass_cap_enforced_on_repeat(self):
        os.environ["SECONDOP_MAX_LLM_PASSES"] = "1"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                cpath = os.path.join(tmp, "c.json")
                with open(cpath, "w", encoding="utf-8") as f:
                    json.dump({"findings": []}, f)
                review.run_full(FIX, out_base=tmp, advisory_path=cpath)        # pass 1
                rep, _, _ = review.run_full(FIX, out_base=tmp, advisory_path=cpath)  # over cap
                self.assertTrue(rep["llm"]["capped"])
        finally:
            os.environ.pop("SECONDOP_MAX_LLM_PASSES", None)


if __name__ == "__main__":
    unittest.main()
