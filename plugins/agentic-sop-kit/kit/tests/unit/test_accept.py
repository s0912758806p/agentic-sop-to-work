# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""單元測試：accept skill（受測功能登錄表登記）。stdlib unittest；subprocess 跑真實 CLI。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(KIT, "skills", "accept", "tool.py")


def _run(data):
    d = tempfile.mkdtemp()
    i, o = os.path.join(d, "in.json"), os.path.join(d, "o.json")
    with open(i, "w", encoding="utf-8") as f:
        json.dump({"schema": "verdict@1", "produced_by": "verdict", "data": data, "trace": []}, f)
    r = subprocess.run([sys.executable, TOOL, "--in", i, "--out", o],
                       capture_output=True, text=True)
    out = json.load(open(o, encoding="utf-8")) if os.path.exists(o) else None
    return r, out


class Accept(unittest.TestCase):
    def test_pass_is_accepted_as_a_draft(self):
        r, out = _run({"verdict": "pass", "defects": 0, "round": 3})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out["schema"], "accepted@1")
        self.assertEqual(out["data"]["rounds"], 3)
        self.assertEqual(out["data"]["draft_status"], "DRAFT", "產出一律 DRAFT")

    def test_reject_is_refused_even_if_routing_sent_it_here(self):
        """不信任路由：手改 branch 條件把 reject 送進來，仍不得放行。"""
        r, out = _run({"verdict": "reject", "defects": 1, "round": 1})
        self.assertNotEqual(r.returncode, 0)
        self.assertIsNone(out, "未通過的草稿不得產生 accepted artifact")

    def test_derived_rounds_carries_its_provenance(self):
        """衍生數字也要有來源：不標出處的話下游誠實檢查會（正確地）當成臆造。"""
        r, out = _run({"verdict": "pass", "defects": 0, "round": 3})
        self.assertEqual(r.returncode, 0, r.stderr)
        sourced = {t["value"] for t in out["trace"]}
        self.assertIn("3", sourced, "rounds 應可溯源到上游 data.round")
        entry = [t for t in out["trace"] if t["value"] == "3"][0]
        self.assertEqual(entry["locator"], "data.round")

    def test_absent_verdict_is_refused(self):
        r, out = _run({"defects": 0})
        self.assertNotEqual(r.returncode, 0)
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
