# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.llm_contract — the three guardrails that keep the
advisory LLM layer honest and capped, ALL enforced in code (not prose):
  • merge clamp        — every LLM finding forced to SOFT / advisory / confidence ≤ 0.5
  • evidence gate      — drop any accusation that doesn't cite a verbatim draft span (or NO SOURCE)
  • settled suppression — drop any finding that re-litigates a slot the deterministic layer settled
Plus the code-enforced pass cap (mirrors SOPKIT_MAX_FIX_RETRIES).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import llm_contract  # noqa: E402
from secondop.model import Finding, NormalizedDraft, Claim  # noqa: E402

DRAFT_TEXT = "Assay 96.5% PASS. Conclusion: stable through 24 months."


class TestCap(unittest.TestCase):
    def test_default_is_one(self):
        os.environ.pop("SECONDOP_MAX_LLM_PASSES", None)
        self.assertEqual(llm_contract.max_passes(), 1)

    def test_env_override_clamped_to_ceiling(self):
        os.environ["SECONDOP_MAX_LLM_PASSES"] = "99"
        try:
            self.assertEqual(llm_contract.max_passes(), 3)  # hard ceiling
        finally:
            os.environ.pop("SECONDOP_MAX_LLM_PASSES", None)


class TestEnvelope(unittest.TestCase):
    def test_envelope_carries_settled_and_focus(self):
        draft = NormalizedDraft(mode="FULL", raw_text=DRAFT_TEXT,
                                sources=[{"value": "96.5"}],
                                claims=[Claim(id="a", value=96.5, sourced=True)])
        det = [Finding(id="#1:x", vector="#1", severity="HARD", origin="deterministic",
                       location="results[0]", claim="verdict PASS", evidence="expected fail",
                       mode_confidence=1.0, settled_key="slot:results[0]")]
        env = llm_contract.build_llm_envelope(draft, det)
        self.assertEqual(env["mode"], "FULL")
        self.assertIn("slot:results[0]", [s["settled_key"] for s in env["already_settled"]])
        self.assertIn("#4", env["focus"])
        self.assertTrue(any("ADVISORY" in r.upper() for r in env["rules"]))


class TestMerge(unittest.TestCase):
    SETTLED = {"slot:results[0]"}

    def test_clamps_to_soft_advisory_and_caps_confidence(self):
        raw = [{"vector": "#4", "location": "conclusion",
                "claim": "stable through 24 months", "evidence": "no 24M timepoint; NO SOURCE",
                "confidence": 0.95}]
        kept, dropped = llm_contract.merge_llm_findings(raw, DRAFT_TEXT, self.SETTLED)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].severity, "SOFT")
        self.assertEqual(kept[0].origin, "advisory")
        self.assertLessEqual(kept[0].mode_confidence, 0.5)

    def test_evidence_gate_drops_uncited_accusation(self):
        raw = [{"vector": "#4", "location": "x",
                "claim": "this is a made up problem not in the draft",
                "evidence": "i just think so", "confidence": 0.4}]
        kept, dropped = llm_contract.merge_llm_findings(raw, DRAFT_TEXT, self.SETTLED)
        self.assertEqual(kept, [])
        self.assertEqual(len(dropped), 1)

    def test_keeps_when_claim_quotes_draft_verbatim(self):
        raw = [{"vector": "#4", "location": "conclusion",
                "claim": "stable through 24 months", "evidence": "unsupported leap"}]
        kept, _ = llm_contract.merge_llm_findings(raw, DRAFT_TEXT, set())
        self.assertEqual(len(kept), 1)

    def test_suppresses_already_settled_slot(self):
        raw = [{"vector": "#1", "location": "results[0]",
                "claim": "stable through 24 months", "evidence": "NO SOURCE"}]
        kept, dropped = llm_contract.merge_llm_findings(raw, DRAFT_TEXT, self.SETTLED)
        self.assertEqual(kept, [])
        self.assertTrue(any("settled" in d["reason"] for d in dropped))


if __name__ == "__main__":
    unittest.main()
