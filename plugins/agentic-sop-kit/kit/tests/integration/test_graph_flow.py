# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Integration：有界退回邊會被走到、會收斂，且退回歷史不會被覆寫掉。

這是「解鎖已出貨儀表」的驗收。改版前整個系統只有一個迴圈（run.py 整條 flow 重跑），
`lib/loop/` 的 stall/budget 儀表被用在最粗的粒度上；退回邊讓同一套儀表下降到單條邊。

控制流仍在程式：退回與否由 branch 的 predicate 依狀態判定
（flow.py 的 `The model never decides the next step.` 不變）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_fixtures as gf  # noqa: E402


class BackEdgeIsWalked(unittest.TestCase):
    def test_plan_accepts_the_bounded_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            r = subprocess.run([sys.executable, gf.RUN, "--flow", flow, "--plan"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("back-edge", r.stdout)

    def test_reject_routes_back_and_second_visit_passes(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            base = os.path.join(d, "runs")
            r = gf.run_flow(flow, base)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            mani = gf.manifest(base)
            self.assertEqual(mani["state"], "OK_FOR_REVIEW")
            names = gf.nodes_walked(mani)
            self.assertEqual(names.count("revise"), 2, mani["path_taken"])
            self.assertIn("accept", names)

    def test_revisit_does_not_destroy_the_first_attempt(self):
        """退回重跑不得覆寫掉前一次的產物——保留退回歷史正是選擇「狀態＝宣告」
        而非中央 store 的理由（store 覆寫，第一次嘗試會消失）。"""
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            base = os.path.join(d, "runs")
            self.assertEqual(gf.run_flow(flow, base).returncode, 0)
            run_dir = os.path.join(base, "g")
            with open(os.path.join(run_dir, "draft.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["data"]["attempt"], 2, "live artifact 應是最新一次")
            archived = os.path.join(run_dir, "draft.visit1.json")
            self.assertTrue(os.path.exists(archived), "第一次嘗試應被歸檔而非消失")
            with open(archived, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["data"]["attempt"], 1)

    def test_path_taken_records_visit_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            base = os.path.join(d, "runs")
            self.assertEqual(gf.run_flow(flow, base).returncode, 0)
            visits = [(p["node"], p["visit"]) for p in gf.manifest(base)["path_taken"]]
            self.assertIn(("revise", 1), visits)
            self.assertIn(("revise", 2), visits)


class TopologyInManifest(unittest.TestCase):
    def test_manifest_carries_the_topology_and_owners(self):
        """下游（second-opinion / alcoa-guard）不必逆向工程就能知道跑了什麼形狀。"""
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            base = os.path.join(d, "runs")
            self.assertEqual(gf.run_flow(flow, base).returncode, 0)
            topo = gf.manifest(base)["topology"]
            self.assertEqual(topo["owners"], {"draft": "revise", "verdict": "review"})
            self.assertEqual(topo["back_edges"],
                             [{"frm": "gate", "to": "revise", "max_revisits": 2}])


class GraphRendering(unittest.TestCase):
    def test_graph_emits_mermaid_with_a_dotted_back_edge(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            r = subprocess.run([sys.executable, gf.RUN, "--flow", flow, "--graph"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("flowchart LR", r.stdout)
            self.assertIn("-.->", r.stdout, "退回邊應以虛線呈現（與原圖一致）")
            self.assertIn("revise", r.stdout)

    def test_graph_is_byte_deterministic(self):
        """文件綁定依賴這點：同一份 flow.json 必須每次產生完全相同的圖。"""
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            outs = {subprocess.run([sys.executable, gf.RUN, "--flow", flow, "--graph"],
                                   capture_output=True, text=True).stdout for _ in range(3)}
            self.assertEqual(len(outs), 1)

    def test_graph_does_not_execute_anything(self):
        with tempfile.TemporaryDirectory() as d:
            flow = gf.graph_flow(d, gf.improving_tool(d))
            base = os.path.join(d, "runs")
            subprocess.run([sys.executable, gf.RUN, "--flow", flow, "--out-base", base, "--graph"],
                           capture_output=True, text=True)
            self.assertFalse(os.path.isdir(base), "--graph 不得產生 run 目錄")


class LegacyFlowsGetNoGraphKeys(unittest.TestCase):
    def test_linear_flow_manifest_has_no_topology_or_path_taken(self):
        """opt-in 的具體含意：沒宣告圖欄位的流程，manifest 形狀不變
        （逐位元比對見 test_legacy_flow.py）。"""
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "runs")
            r = subprocess.run([sys.executable, gf.RUN, "--out-base", base, "--run-id", "L"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            mani = gf.manifest(base, "L")
            self.assertNotIn("topology", mani)
            self.assertNotIn("path_taken", mani)


if __name__ == "__main__":
    unittest.main(verbosity=2)
