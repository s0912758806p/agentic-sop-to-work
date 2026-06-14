# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.ack — the human acknowledgement that unblocks the gate.

You can only acknowledge a run that HAS a Second Opinion review (review first, then ack),
and the .ack record captures who/when so misuse is at least visible in the audit trail.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import ack, gate  # noqa: E402


def _project_with_review(tmp, run_id="run_20260601_000000_abcd"):
    os.makedirs(os.path.join(tmp, ".agentic-sop-runs", run_id))
    rd = os.path.join(tmp, ".second-opinion-runs", run_id)
    os.makedirs(rd)
    with open(os.path.join(rd, "second_opinion.json"), "w", encoding="utf-8") as f:
        json.dump({"verdict": "ADVISORY_ONLY"}, f)
    return run_id


class TestAck(unittest.TestCase):
    def test_ack_marks_run_acknowledged(self):
        with tempfile.TemporaryDirectory() as tmp:
            rid = _project_with_review(tmp)
            path, rec = ack.ack(tmp, run_id=rid, note="looks fine", user="alice")
            self.assertTrue(os.path.exists(path))
            self.assertTrue(gate.is_acked(tmp, rid))
            self.assertEqual(rec["run_id"], rid)
            self.assertEqual(rec["by"], "alice")
            self.assertEqual(rec["note"], "looks fine")

    def test_ack_defaults_to_latest_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            rid = _project_with_review(tmp)
            _, rec = ack.ack(tmp)
            self.assertEqual(rec["run_id"], rid)

    def test_ack_refuses_when_no_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".agentic-sop-runs", "run_x"))  # run but no review
            with self.assertRaises(ack.AckError):
                ack.ack(tmp, run_id="run_x")

    def test_ack_refuses_when_no_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ack.AckError):
                ack.ack(tmp)


if __name__ == "__main__":
    unittest.main()
