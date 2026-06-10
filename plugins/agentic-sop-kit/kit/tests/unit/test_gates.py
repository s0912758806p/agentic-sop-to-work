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

    def test_stdout_contains_pass(self):
        art = {"data": {"exit": 0, "stdout": "all PASS here", "stderr": ""}}
        ok, _ = gates.run_gate("cmd_gate", art, {"stdout_contains": "PASS"})
        self.assertTrue(ok)


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


class GetHelper(unittest.TestCase):
    def test_found(self):
        ok, val = gates._get({"a": {"b": 5}}, "a.b")
        self.assertTrue(ok)
        self.assertEqual(val, 5)

    def test_missing_key(self):
        ok, val = gates._get({"a": {}}, "a.b")
        self.assertFalse(ok)
        self.assertIsNone(val)


class TraceGate(unittest.TestCase):
    def test_pass_when_values_traceable(self):
        art = {"data": {"claims": [12.0, 7.0]},
               "trace": [{"value": "12.0", "source": "in.txt"}, {"value": "7.0", "source": "in.txt"}]}
        ok, _ = gates.run_gate("trace_gate", art, {"fields": "claims"})
        self.assertTrue(ok)

    def test_fail_on_fabricated_value(self):
        art = {"data": {"claims": [12.0, 999.0]},
               "trace": [{"value": "12.0", "source": "in.txt"}]}
        ok, reason = gates.run_gate("trace_gate", art, {"fields": "claims"})
        self.assertFalse(ok)
        self.assertIn("999", reason)


class RecomputeGate(unittest.TestCase):
    def test_count_match(self):
        art = {"data": {"rows": [1, 2, 3], "n": 3}}
        ok, _ = gates.run_gate("recompute_gate", art, {"op": "count", "over": "rows", "equals": "n"})
        self.assertTrue(ok)

    def test_sum_mismatch(self):
        art = {"data": {"vals": [1, 2, 3], "total": 99}}
        ok, reason = gates.run_gate("recompute_gate", art, {"op": "sum", "over": "vals", "equals": "total"})
        self.assertFalse(ok)
        self.assertIn("mismatch", reason)


if __name__ == "__main__":
    unittest.main()
