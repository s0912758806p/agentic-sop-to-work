# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Unit: be_api — emits an api@1 response that satisfies the example's schema_gate."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KIT)  # kit root → sopkit
from sopkit import gates  # noqa: E402

TOOL = os.path.join(KIT, "skills", "be_api", "tool.py")


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


class TestBeApi(unittest.TestCase):
    def test_response_passes_schema_gate(self):
        r, art = _run({})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((art["schema"], art["produced_by"]), ("api@1", "be_api"))
        self.assertEqual(gates.run_gate("schema_gate", art, {"required": ["id", "name"]}), (True, "ok"))

    def test_gate_catches_a_malformed_response(self):
        _, art = _run({})
        del art["data"]["name"]
        self.assertFalse(gates.run_gate("schema_gate", art, {"required": ["id", "name"]})[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
