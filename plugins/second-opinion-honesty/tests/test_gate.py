# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.gate — the pure ack-gate decision (做法 3).

The decision is a pure function so it is trivially testable; the hook is a thin IO
wrapper around it. The gate enforces THAT a human acknowledged a Second Opinion review
of the latest DRAFT run — never WHAT they decided — and is anti-loop capped.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import gate  # noqa: E402


class TestHelpers(unittest.TestCase):
    def test_max_ack_retries_default_and_override(self):
        os.environ.pop("SECONDOP_MAX_ACK_RETRIES", None)
        self.assertEqual(gate.max_ack_retries(), 3)
        os.environ["SECONDOP_MAX_ACK_RETRIES"] = "5"
        try:
            self.assertEqual(gate.max_ack_retries(), 5)
        finally:
            os.environ.pop("SECONDOP_MAX_ACK_RETRIES", None)

    def test_latest_run_id_picks_newest(self):
        with tempfile.TemporaryDirectory() as proj:
            base = os.path.join(proj, ".agentic-sop-runs")
            os.makedirs(os.path.join(base, "run_20260101_000000_aaaa"))
            os.makedirs(os.path.join(base, "run_20260201_000000_bbbb"))
            self.assertEqual(gate.latest_run_id(proj), "run_20260201_000000_bbbb")

    def test_latest_run_id_none_when_absent(self):
        with tempfile.TemporaryDirectory() as proj:
            self.assertIsNone(gate.latest_run_id(proj))

    def test_review_and_ack_detection(self):
        with tempfile.TemporaryDirectory() as proj:
            rid = "run_x"
            d = os.path.join(proj, ".second-opinion-runs", rid)
            os.makedirs(d)
            self.assertFalse(gate.review_exists(proj, rid))
            open(os.path.join(d, "second_opinion.json"), "w").close()
            self.assertTrue(gate.review_exists(proj, rid))
            self.assertFalse(gate.is_acked(proj, rid))
            open(os.path.join(d, ".ack"), "w").close()
            self.assertTrue(gate.is_acked(proj, rid))


class TestDecide(unittest.TestCase):
    def test_not_opted_in_allows_stop(self):
        block, _, n = gate.decide(False, "run_x", False, False, False, 0, 3)
        self.assertFalse(block)
        self.assertEqual(n, 0)

    def test_no_run_to_review_allows_stop(self):
        block, _, _ = gate.decide(True, None, False, False, False, 0, 3)
        self.assertFalse(block)

    def test_reviewed_and_acked_allows_stop(self):
        block, _, _ = gate.decide(True, "run_x", True, True, False, 0, 3)
        self.assertFalse(block)

    def test_no_review_blocks(self):
        block, reason, n = gate.decide(True, "run_x", False, False, False, 0, 3)
        self.assertTrue(block)
        self.assertEqual(n, 1)
        self.assertIn("run_x", reason)

    def test_review_but_not_acked_blocks(self):
        block, reason, _ = gate.decide(True, "run_x", True, False, False, 0, 3)
        self.assertTrue(block)
        self.assertIn("acknowledg", reason.lower())

    def test_anti_loop_cap_hands_to_human(self):
        # already in a stop-hook continuation and at the cap -> stop blocking
        block, reason, _ = gate.decide(True, "run_x", False, False, True, 3, 3)
        self.assertFalse(block)
        self.assertIn("human", reason.lower())


if __name__ == "__main__":
    unittest.main()
