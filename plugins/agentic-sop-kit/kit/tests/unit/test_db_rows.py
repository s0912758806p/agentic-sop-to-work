# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Unit: db_rows — the stated total is re-derivable, so recompute_gate passes; a total that
does not add up is caught."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KIT)  # kit root → sopkit
from sopkit import gates  # noqa: E402

TOOL = os.path.join(KIT, "skills", "db_rows", "tool.py")


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


ARGS = {"op": "sum", "over": "rows", "equals": "total"}


class TestDbRows(unittest.TestCase):
    def test_total_recomputes(self):
        r, art = _run({})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(art["schema"], "rows@1")
        self.assertEqual(art["data"]["total"], sum(art["data"]["rows"]))
        self.assertEqual(gates.run_gate("recompute_gate", art, ARGS), (True, "ok"))

    def test_wrong_total_is_caught(self):
        _, art = _run({})
        art["data"]["total"] += 1
        self.assertFalse(gates.run_gate("recompute_gate", art, ARGS)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
