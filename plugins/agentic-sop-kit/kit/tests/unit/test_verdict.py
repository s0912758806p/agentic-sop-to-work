# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""單元測試：verdict skill（受測功能登錄表登記）。stdlib unittest；subprocess 跑真實 CLI。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(KIT, "skills", "verdict", "tool.py")


def _run(data):
    d = tempfile.mkdtemp()
    i, o = os.path.join(d, "in.json"), os.path.join(d, "o.json")
    with open(i, "w", encoding="utf-8") as f:
        json.dump({"schema": "draft@1", "produced_by": "draft", "data": data,
                   "trace": [{"value": "1", "source": "x", "locator": "line 1"}]}, f)
    r = subprocess.run([sys.executable, TOOL, "--in", i, "--out", o],
                       capture_output=True, text=True)
    out = json.load(open(o, encoding="utf-8")) if os.path.exists(o) else None
    return r, out


class Verdict(unittest.TestCase):
    def test_open_defects_reject(self):
        r, out = _run({"defects": 1, "round": 2})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out["schema"], "verdict@1")
        self.assertEqual(out["data"]["verdict"], "reject")

    def test_no_defects_pass(self):
        r, out = _run({"defects": 0, "round": 3})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out["data"]["verdict"], "pass")

    def test_trace_is_passed_through(self):
        _, out = _run({"defects": 0, "round": 1})
        self.assertEqual(len(out["trace"]), 1, "trace 應逐層透傳，交接不遺失")

    def test_missing_defects_fails_loud_rather_than_guessing(self):
        r, out = _run({"round": 1})
        self.assertNotEqual(r.returncode, 0, "缺 defects 不得臆測判定")
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
