# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Unit tests for deterministic control-flow helpers."""
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "lib"))
import flow  # noqa: E402


class Predicate(unittest.TestCase):
    def test_eq(self):
        self.assertTrue(flow.eval_predicate({"path": "a", "op": "==", "value": 1}, {"a": 1}))
        self.assertFalse(flow.eval_predicate({"path": "a", "op": "==", "value": 2}, {"a": 1}))

    def test_cmp_and_in(self):
        self.assertTrue(flow.eval_predicate({"path": "n", "op": ">", "value": 3}, {"n": 5}))
        self.assertTrue(flow.eval_predicate({"path": "k", "op": "in", "value": ["x", "y"]}, {"k": "y"}))

    def test_exists(self):
        self.assertTrue(flow.eval_predicate({"path": "a.b", "op": "exists"}, {"a": {"b": 0}}))
        self.assertFalse(flow.eval_predicate({"path": "a.c", "op": "exists"}, {"a": {"b": 0}}))

    def test_missing_path_is_false(self):
        self.assertFalse(flow.eval_predicate({"path": "x", "op": "==", "value": 1}, {}))

    def test_unknown_op_is_false(self):
        self.assertFalse(flow.eval_predicate({"path": "a", "op": "~=", "value": 1}, {"a": 1}))

    def test_type_mismatch_is_false_not_raise(self):
        self.assertFalse(flow.eval_predicate({"path": "a", "op": "<", "value": 3}, {"a": "x"}))


class ResolveBranch(unittest.TestCase):
    def test_first_match_wins(self):
        cases = [{"when": {"path": "s", "op": "==", "value": "OOS"}, "goto": "investigate"},
                 {"default": True, "goto": "release"}]
        goto, _ = flow.resolve_branch(cases, {"s": "OOS"})
        self.assertEqual(goto, "investigate")

    def test_default_fallthrough(self):
        cases = [{"when": {"path": "s", "op": "==", "value": "OOS"}, "goto": "investigate"},
                 {"default": True, "goto": "release"}]
        goto, _ = flow.resolve_branch(cases, {"s": "OK"})
        self.assertEqual(goto, "release")

    def test_no_match_no_default(self):
        goto, reason = flow.resolve_branch([{"when": {"path": "s", "op": "==", "value": "OOS"}, "goto": "x"}], {"s": "OK"})
        self.assertIsNone(goto)
        self.assertIn("no", reason.lower())

    def test_default_first_still_routes_to_match(self):
        cases = [{"default": True, "goto": "release"},
                 {"when": {"path": "s", "op": "==", "value": "OOS"}, "goto": "investigate"}]
        goto, _ = flow.resolve_branch(cases, {"s": "OOS"})
        self.assertEqual(goto, "investigate")  # placement-independent: when wins over earlier default


if __name__ == "__main__":
    unittest.main()
