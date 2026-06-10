# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Unit tests for the deterministic gate library."""
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "lib"))
import gates  # noqa: E402


class CmdGate(unittest.TestCase):
    def test_pass_on_exit_0(self):
        art = {"data": {"exit": 0, "stdout": "build ok", "stderr": ""}}
        ok, _ = gates.run_gate("cmd_gate", art, {})
        self.assertTrue(ok)

    def test_fail_on_nonzero(self):
        art = {"data": {"exit": 1, "stdout": "", "stderr": "boom"}}
        ok, reason = gates.run_gate("cmd_gate", art, {})
        self.assertFalse(ok)
        self.assertIn("boom", reason)

    def test_stdout_contains(self):
        art = {"data": {"exit": 0, "stdout": "no match", "stderr": ""}}
        ok, _ = gates.run_gate("cmd_gate", art, {"stdout_contains": "PASS"})
        self.assertFalse(ok)


class SchemaGate(unittest.TestCase):
    def test_pass(self):
        art = {"data": {"id": 1, "name": "x"}}
        ok, _ = gates.run_gate("schema_gate", art, {"required": ["id", "name"]})
        self.assertTrue(ok)

    def test_fail_lists_missing(self):
        art = {"data": {"id": 1}}
        ok, reason = gates.run_gate("schema_gate", art, {"required": ["id", "name"]})
        self.assertFalse(ok)
        self.assertIn("name", reason)


class Unknown(unittest.TestCase):
    def test_unknown_gate(self):
        ok, reason = gates.run_gate("nope", {"data": {}}, {})
        self.assertFalse(ok)
        self.assertIn("unknown", reason.lower())


if __name__ == "__main__":
    unittest.main()
