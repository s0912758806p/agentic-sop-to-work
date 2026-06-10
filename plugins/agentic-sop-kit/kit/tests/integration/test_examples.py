# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Integration: the shipped per-domain example flows run dependency-free and their gates pass."""
import os
import subprocess
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(KIT, "workflow", "run.py")
EX = os.path.join(KIT, "workflow", "examples")


def _run(flow):
    with tempfile.TemporaryDirectory() as d:
        return subprocess.run([sys.executable, RUN, "--flow", os.path.join(EX, flow), "--out-base", d],
                              capture_output=True, text=True)


class Examples(unittest.TestCase):
    def test_fe_cmd_gate(self):
        r = _run("fe.json"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_be_schema_gate(self):
        r = _run("be.json"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_db_recompute_gate(self):
        r = _run("db.json"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_ai_trace_gate(self):
        r = _run("ai.json"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
