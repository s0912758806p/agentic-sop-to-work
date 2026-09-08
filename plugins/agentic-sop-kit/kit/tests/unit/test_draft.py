# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""單元測試：draft skill（受測功能登錄表登記）。stdlib unittest；subprocess 跑真實 CLI。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(KIT, "skills", "draft", "tool.py")


def _run(in_obj):
    d = tempfile.mkdtemp()
    i, o = os.path.join(d, "in.json"), os.path.join(d, "o.json")
    if in_obj is not None:
        with open(i, "w", encoding="utf-8") as f:
            json.dump(in_obj, f)
    r = subprocess.run([sys.executable, TOOL, "--in", i, "--out", o],
                       capture_output=True, text=True)
    data = json.load(open(o, encoding="utf-8")) if os.path.exists(o) else None
    return r, data


class Draft(unittest.TestCase):
    def test_missing_input_is_a_first_draft(self):
        """第一次進入節點時 $RUN/verdict.json 還不存在——不得因此失敗。"""
        r, data = _run(None)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(data["schema"], "draft@1")
        self.assertEqual(data["data"]["round"], 1)
        self.assertEqual(data["data"]["defects"], 2)

    def test_verdict_input_advances_the_round_and_fixes_one_defect(self):
        r, data = _run({"schema": "verdict@1", "produced_by": "verdict",
                        "data": {"verdict": "reject", "defects": 2, "round": 1}, "trace": []})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((data["data"]["round"], data["data"]["defects"]), (2, 1))
        self.assertTrue(data["data"]["addressed"])

    def test_defects_never_go_negative(self):
        r, data = _run({"schema": "verdict@1", "produced_by": "verdict",
                        "data": {"verdict": "pass", "defects": 0, "round": 5}, "trace": []})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(data["data"]["defects"], 0)

    def test_non_verdict_artifact_is_treated_as_a_fresh_input(self):
        r, data = _run({"schema": "readings@1", "produced_by": "extract",
                        "data": {"readings": [], "skipped": []}, "trace": []})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(data["data"]["round"], 1)

    def test_deterministic_for_the_same_input(self):
        art = {"schema": "verdict@1", "produced_by": "verdict",
               "data": {"verdict": "reject", "defects": 2, "round": 1}, "trace": []}
        self.assertEqual(_run(art)[1], _run(art)[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
