# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""單元測試：extract skill（受測功能登錄表登記）。stdlib unittest；subprocess 跑真實 CLI。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(KIT, "skills", "extract", "tool.py")


def _run(args):
    return subprocess.run([sys.executable, TOOL] + args, capture_output=True, text=True)


class TestExtract(unittest.TestCase):
    def _extract(self, text, extra=None):
        d = tempfile.mkdtemp()
        i, o = os.path.join(d, "in.txt"), os.path.join(d, "o.json")
        open(i, "w", encoding="utf-8").write(text)
        r = _run(["--in", i, "--out", o] + (extra or []))
        data = json.load(open(o, encoding="utf-8")) if os.path.exists(o) else None
        return r, data

    def test_broadened_grammar(self):
        r, data = self._extract("yield: 1,234\nconc: 1.2e3\nweight: 250 mg\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(x["value"] for x in data["data"]["readings"]), [250.0, 1200.0, 1234.0])

    def test_failloud_on_malformed_digit_line(self):
        r, _ = self._extract("ok: 5\nbad: v1.2.3.4-rc5\n")
        self.assertNotEqual(r.returncode, 0, "含數字無法解析的行應 fail-loud")
        self.assertIn("bad", r.stderr + r.stdout)

    def test_allow_unparsed_records_skipped(self):
        r, data = self._extract("ok: 5\nbad: v1.2.3.4\n", ["--allow-unparsed"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(data["data"]["skipped"], "skipped 應記錄")

    def test_comments_and_text_ignored(self):
        r, data = self._extract("# comment\n\nnote: no number here\nx: 3\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x["key"] for x in data["data"]["readings"]], ["x"])
        self.assertEqual(data["data"]["skipped"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
