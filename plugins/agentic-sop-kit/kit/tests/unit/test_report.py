"""單元測試：report skill（受測功能登錄表登記）。stdlib unittest；subprocess 跑真實 CLI。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(KIT, "skills", "report", "tool.py")


def _stats_artifact(stats, skipped=None, trace=None):
    return {"schema": "stats@1", "produced_by": "compute",
            "data": {"stats": stats, "skipped": skipped or []},
            "trace": trace or []}


class TestReport(unittest.TestCase):
    def _report(self, artifact):
        d = tempfile.mkdtemp()
        i, o = os.path.join(d, "in.json"), os.path.join(d, "report.md")
        json.dump(artifact, open(i, "w", encoding="utf-8"))
        r = subprocess.run([sys.executable, TOOL, "--in", i, "--out", o], capture_output=True, text=True)
        md = open(o, encoding="utf-8").read() if os.path.exists(o) else ""
        return r, md

    def test_draft_summary_and_trace(self):
        r, md = self._report(_stats_artifact(
            {"count": 2, "sum": 7.0, "mean": 3.5, "min": 3.0, "max": 4.0},
            trace=[{"value": "3", "source": "in.txt", "locator": "line 1"}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DRAFT", md)
        self.assertIn("## Summary", md)
        self.assertIn("count: 2", md)
        self.assertIn("來源追溯", md)
        self.assertIn("in.txt:line 1", md)

    def test_skipped_section_surfaced(self):
        r, md = self._report(_stats_artifact(
            {"count": 1, "sum": 1.0, "mean": 1.0, "min": 1.0, "max": 1.0},
            skipped=[{"line": 9, "text": "v1.2.3.4"}]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("未解析行", md)
        self.assertIn("line 9", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
