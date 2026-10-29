# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Unit: ai_claims — every claim carries a trace entry, so trace_gate passes; a value the
model invents (not in the trace) is what trace_gate exists to block."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KIT)  # kit root → sopkit
from sopkit import gates  # noqa: E402

TOOL = os.path.join(KIT, "skills", "ai_claims", "tool.py")


def _run(inp_obj):
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "in.json"), os.path.join(d, "out.json")
        with open(i, "w", encoding="utf-8") as f:
            json.dump(inp_obj, f)
        r = subprocess.run([sys.executable, TOOL, "--in", i, "--out", o], capture_output=True, text=True)
        art = None
        if os.path.exists(o):
            with open(o, encoding="utf-8") as f:
                art = json.load(f)
        return r, art


class TestAiClaims(unittest.TestCase):
    SRC = {"schema": "src@1", "produced_by": "seed", "data": {"source": [12, 7]}, "trace": []}

    def test_claims_are_traced(self):
        r, art = _run(self.SRC)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(art["schema"], "claims@1")
        self.assertEqual(art["data"]["claims"], [12, 7])
        self.assertEqual([t["locator"] for t in art["trace"]], ["source[0]", "source[1]"])
        self.assertEqual(gates.run_gate("trace_gate", art, {"fields": "claims"}), (True, "ok"))

    def test_invented_value_is_blocked(self):
        _, art = _run(self.SRC)
        art["data"]["claims"].append(99)
        ok, why = gates.run_gate("trace_gate", art, {"fields": "claims"})
        self.assertFalse(ok)
        self.assertIn("99", why)

    def test_empty_source(self):
        r, art = _run({"schema": "src@1", "produced_by": "seed", "data": {}, "trace": []})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((art["data"]["claims"], art["trace"]), ([], []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
