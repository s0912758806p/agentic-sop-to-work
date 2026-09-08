# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Integration：退回邊的上界在**程式**裡，不在散文裡。

用 churning tool——每次重訪產物都真的變了（attempt 遞增），所以進度感測器看得到進度、
不會判 idle；唯一能停下這個迴圈的就是宣告的 `max_revisits`。這正是 kit 既有雙終止
（budget ＋ stall，先到者停）在單條邊上的 budget 那一半。

紅線：撞上界後不得繼續往下走、不得佯稱成功——必須 STOP 交人。
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_fixtures as gf  # noqa: E402


class RevisitBoundIsEnforced(unittest.TestCase):
    def test_hitting_the_bound_stops_with_a_failed_state(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.churning_tool(d), max_revisits=2)
            base = os.path.join(d, "runs")
            r = gf.run_flow(flow, base)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            mani = gf.manifest(base)
            self.assertEqual(mani["state"], "FAILED")
            self.assertTrue(mani["human_review_required"])

    def test_does_not_fall_through_to_accept(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.churning_tool(d), max_revisits=2)
            base = os.path.join(d, "runs")
            gf.run_flow(flow, base)
            self.assertNotIn("accept", gf.nodes_walked(gf.manifest(base)),
                             "撞上界後不得繼續走到 accept、佯稱成功")

    def test_manifest_names_the_edge_and_the_bound(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.churning_tool(d), max_revisits=2)
            base = os.path.join(d, "runs")
            gf.run_flow(flow, base)
            mani = gf.manifest(base)
            self.assertTrue(mani.get("revisit_exhausted"), mani)
            self.assertEqual(mani["back_edge"],
                             {"frm": "gate", "to": "revise", "max_revisits": 2})

    def test_visits_equal_one_plus_the_bound(self):
        """封頂精確：初訪 1 次 ＋ max_revisits 次重訪，不多不少。"""
        for bound, expected in ((1, 2), (3, 4)):
            with self.subTest(max_revisits=bound):
                with tempfile.TemporaryDirectory() as d:
                    flow = gf.graph_flow(d, gf.churning_tool(d), max_revisits=bound)
                    base = os.path.join(d, "runs")
                    gf.run_flow(flow, base)
                    names = gf.nodes_walked(gf.manifest(base))
                    self.assertEqual(names.count("revise"), expected, names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
