# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""單元測試：compute skill（受測功能登錄表登記）。stdlib unittest；subprocess 跑真實 CLI。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(KIT, "skills", "compute", "tool.py")


def _readings_artifact(readings, skipped=None):
    return {"schema": "readings@1", "produced_by": "extract",
            "data": {"readings": readings, "skipped": skipped or []},
            "trace": [{"value": str(r["value"]), "source": "x", "locator": f"line {i+1}"}
                      for i, r in enumerate(readings)]}


class TestCompute(unittest.TestCase):
    def _compute(self, artifact):
        d = tempfile.mkdtemp()
        i, o = os.path.join(d, "in.json"), os.path.join(d, "o.json")
        json.dump(artifact, open(i, "w", encoding="utf-8"))
        r = subprocess.run([sys.executable, TOOL, "--in", i, "--out", o], capture_output=True, text=True)
        data = json.load(open(o, encoding="utf-8")) if os.path.exists(o) else None
        return r, data

    def test_stats_correct(self):
        r, data = self._compute(_readings_artifact([{"key": "a", "value": 2.0},
                                                    {"key": "b", "value": 4.0},
                                                    {"key": "c", "value": 6.0}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        s = data["data"]["stats"]
        self.assertEqual((s["count"], s["sum"], s["mean"], s["min"], s["max"]), (3, 12.0, 4.0, 2.0, 6.0))
        self.assertEqual(data["schema"], "stats@1")

    def test_skipped_passthrough(self):
        r, data = self._compute(_readings_artifact([{"key": "a", "value": 1.0}],
                                                   skipped=[{"line": 5, "text": "junk 9z9"}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(data["data"]["skipped"], [{"line": 5, "text": "junk 9z9"}], "skipped 應透傳到下游")

    def test_empty_readings_completes(self):
        r, data = self._compute(_readings_artifact([]))
        self.assertEqual(r.returncode, 0, r.stderr)
        s = data["data"]["stats"]
        self.assertEqual(s["count"], 0)
        self.assertIsNone(s["mean"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
