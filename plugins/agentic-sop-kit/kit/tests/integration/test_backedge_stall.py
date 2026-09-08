# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Integration：進度感測器真的下降到**單條退回邊**的粒度。

改版前 `lib/loop/progress.py` 只在「整條 flow 重跑」那一個迴圈上量進度。這裡用 frozen tool
——每次重訪產出逐位元相同——驗證同一套 idle 判定在單條退回邊上生效，而且**比宣告的上界更早**
停下來（雙終止：先到者停）。

進度只從感測器輸出量測（產物內容），不看模型自述，也不看「重訪了幾次」本身。
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_fixtures as gf  # noqa: E402


class BackEdgeStall(unittest.TestCase):
    def test_identical_output_across_revisits_is_idle(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.frozen_tool(d), max_revisits=9)
            base = os.path.join(d, "runs")
            r = gf.run_flow(flow, base, "g", "--stall-window", "2")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            mani = gf.manifest(base)
            self.assertTrue(mani.get("stalled"), mani)
            self.assertEqual(mani.get("stall_reason"), "idle")

    def test_stall_beats_the_bound_when_there_is_no_progress(self):
        """上界是 9，但無進度時不該轉 9 圈——感測器先停。"""
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.frozen_tool(d), max_revisits=9)
            base = os.path.join(d, "runs")
            gf.run_flow(flow, base, "g", "--stall-window", "2")
            mani = gf.manifest(base)
            self.assertLess(gf.nodes_walked(mani).count("revise"), 9)
            self.assertFalse(mani.get("revisit_exhausted"),
                             "應由 stall 停止，而非撞上界")

    def test_stall_names_the_back_edge_it_stalled_on(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.frozen_tool(d), max_revisits=9)
            base = os.path.join(d, "runs")
            gf.run_flow(flow, base, "g", "--stall-window", "2")
            mani = gf.manifest(base)
            self.assertIn("revise", str(mani.get("back_edge", "")))
            self.assertTrue(mani.get("repeated_signature"), mani)

    def test_stall_window_zero_disables_the_edge_sensor(self):
        """`--stall-window 0` 關閉 stall（既有語意），此時只剩上界會停。"""
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.frozen_tool(d), max_revisits=2)
            base = os.path.join(d, "runs")
            gf.run_flow(flow, base, "g", "--stall-window", "0")
            mani = gf.manifest(base)
            self.assertFalse(mani.get("stalled"))
            self.assertTrue(mani.get("revisit_exhausted"), mani)


if __name__ == "__main__":
    unittest.main(verbosity=2)
