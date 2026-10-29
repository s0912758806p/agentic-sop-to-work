# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""safe_print must never raise on a console that cannot encode the engine's bilingual / emoji
output (Windows cp950 / cp1252 without PYTHONIOENCODING)."""
import io
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KIT)  # kit root → sopkit
from sopkit.console import safe_print  # noqa: E402

MSG = "  ✅ 流程完成 → report.md ｜ 🧹 pruned"


class SafePrint(unittest.TestCase):
    def _stream(self, enc):
        # newline="\n": no CRLF translation on Windows, so the bytes are what safe_print wrote
        return io.TextIOWrapper(io.BytesIO(), encoding=enc, errors="strict", newline="\n")

    def test_plain_print_would_crash(self):
        s = self._stream("cp1252")
        with self.assertRaises(UnicodeEncodeError):
            print(MSG, file=s)

    def test_degrades_on_cp1252_and_cp950(self):
        for enc in ("cp1252", "cp950"):
            s = self._stream(enc)
            safe_print(MSG, "tail", file=s)
            s.flush()
            out = s.buffer.getvalue().decode(enc)
            self.assertIn("report.md", out)
            self.assertTrue(out.endswith("tail\n"), out)

    def test_utf8_untouched(self):
        s = self._stream("utf-8")
        safe_print(MSG, file=s)
        s.flush()
        self.assertEqual(s.buffer.getvalue().decode("utf-8"), MSG + "\n")


if __name__ == "__main__":
    unittest.main()
