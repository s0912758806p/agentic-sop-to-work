# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Unit tests：拓撲的合法性在 `--plan` 期就確定性地判掉，不必跑。

這是改版最高價值的一塊。`agentic-workflow-audit` 的稽核維度 2 說
「FAIL：所有步驟讀寫同一個大的共享狀態 / context，**無誰給誰什麼的契約**」——
`read-before-write` 與 `唯一 writer` 就是那句話的可執行版本：
節點讀了沒人在所有路徑上寫過的欄位 → 契約有洞；兩個節點宣告寫同一欄位 → 所有權不明＝黑板。

`unbounded cycle` 則是 forward-only（`kit/SOP.md:14`）的替代品：不再禁止環，
而是要求每個環至少經過一條宣告了上界的退回邊。確定性沒有讓步，只是從「禁止」變成「有界才准」。
"""
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "lib"))
import graph  # noqa: E402


def _tool(name, **kw):
    st = {"skill": name, "tool": f"skills/{name}/tool.py", "in": "$INPUT", "out": f"$RUN/{name}.json"}
    st.update(kw)
    return st


def _flow(*steps, name="t"):
    return {"name": name, "steps": list(steps)}


def _problems(flow):
    problems, _ = graph.analyze(flow)
    return problems


def _joined(flow):
    return " | ".join(_problems(flow))


class LinearFlowsAreClean(unittest.TestCase):
    def test_plain_linear_flow_has_no_problems(self):
        self.assertEqual(_problems(_flow(_tool("a"), _tool("b"), _tool("c"))), [])

    def test_steps_without_skill_or_id_are_still_nodes(self):
        """fe.json 的 cmd 步驟既無 skill 也無 id——不得因此崩掉或誤判不可達。"""
        self.assertEqual(_problems(_flow({"cmd": "true", "out": "$RUN/x.json"})), [])


class MalformedSteps(unittest.TestCase):
    def test_step_with_no_tool_cmd_or_branch_is_malformed(self):
        """改版前由 print_plan 內聯檢查；移進 analyze 以保持單一權威。"""
        flow = _flow({"skill": "ghost", "out": "$RUN/x.json"})
        j = _joined(flow)
        self.assertIn("ghost", j)
        self.assertIn("malformed", j.lower())

    def test_map_over_step_is_not_malformed(self):
        flow = _flow(_tool("m", map_over="items"))
        self.assertEqual(_problems(flow), [])


class Reachability(unittest.TestCase):
    def test_node_after_an_always_branching_step_is_unreachable(self):
        # branch 一律跳走（run.py 的 branch 分支不 fall-through），所以 orphan 永遠到不了。
        flow = _flow(
            {"id": "b", "branch": "$RUN/a.json",
             "cases": [{"default": True, "goto": "end"}]},
            _tool("orphan"),
            _tool("end"),
        )
        self.assertIn("orphan", _joined(flow))
        self.assertIn("unreachable", _joined(flow).lower())

    def test_reachable_via_branch_target_is_not_flagged(self):
        flow = _flow(
            {"id": "b", "branch": "$RUN/a.json",
             "cases": [{"when": {"path": "v", "op": "==", "value": 1}, "goto": "x"},
                       {"default": True, "goto": "y"}]},
            _tool("x"), _tool("y"),
        )
        self.assertEqual(_problems(flow), [])


class DanglingAndAmbiguousTargets(unittest.TestCase):
    def test_goto_naming_a_nonexistent_step_is_a_problem(self):
        flow = _flow({"id": "b", "branch": "$RUN/a.json",
                      "cases": [{"default": True, "goto": "nowhere"}]}, _tool("end"))
        self.assertIn("nowhere", _joined(flow))

    def test_duplicate_name_targeted_by_a_goto_is_ambiguous(self):
        flow = _flow({"id": "b", "branch": "$RUN/a.json",
                      "cases": [{"default": True, "goto": "dup"}]},
                     _tool("dup"), _tool("dup"))
        self.assertIn("duplicate", _joined(flow).lower())

    def test_duplicate_name_never_targeted_is_not_a_problem(self):
        """與執行期一致：沒有 goto 指向它，重複命名不影響路由（既有 --plan 測試依賴此行為）。"""
        self.assertEqual(_problems(_flow(_tool("dup"), _tool("dup"))), [])


class ReadBeforeWrite(unittest.TestCase):
    def test_reading_a_field_nobody_writes_is_a_problem(self):
        flow = _flow(_tool("a", writes=["task"]), _tool("b", reads=["findings"]))
        self.assertIn("findings", _joined(flow))

    def test_reading_a_field_written_upstream_is_fine(self):
        flow = _flow(_tool("a", writes=["task"]), _tool("b", reads=["task"], writes=["diff"]))
        self.assertEqual(_problems(flow), [])

    def test_reading_a_field_written_only_downstream_is_a_problem(self):
        """順序要對：下游才寫的欄位，上游讀不到。"""
        flow = _flow(_tool("a", reads=["diff"]), _tool("b", writes=["diff"]))
        self.assertIn("diff", _joined(flow))

    def test_field_written_on_only_one_branch_is_not_guaranteed(self):
        """必須是**所有**路徑都寫過才算有契約——只有一條分支寫的欄位不算。"""
        flow = _flow(
            {"id": "b", "branch": "$RUN/a.json",
             "cases": [{"when": {"path": "v", "op": "==", "value": 1}, "goto": "left"},
                       {"default": True, "goto": "right"}]},
            _tool("left", writes=["diff"]),
            _tool("right"),
            _tool("join", reads=["diff"]),
        )
        # left 寫了 diff，right 沒寫；join 在兩條路徑之後 → 不保證。
        self.assertIn("diff", _joined(flow))

    def test_field_written_before_the_branch_is_guaranteed_on_every_path(self):
        """唯一 writer 在分岔**之前** → 每條路徑都經過它，契約成立。

        （「兩條分支各自寫同一欄位」不是這裡的合法解——那違反唯一 writer，
        見 SingleWriterOwnership。所有權與 read-before-write 是同一套規則的兩面。）
        """
        flow = _flow(
            _tool("seed", writes=["diff"]),
            {"id": "b", "branch": "$RUN/a.json",
             "cases": [{"when": {"path": "v", "op": "==", "value": 1}, "goto": "left"},
                       {"default": True, "goto": "right"}]},
            _tool("left"),
            _tool("right"),
            _tool("join", reads=["diff"]),
        )
        self.assertEqual(_problems(flow), [])


class SingleWriterOwnership(unittest.TestCase):
    def test_two_nodes_writing_the_same_field_is_a_conflict(self):
        """欄位級所有權：一個欄位只能有一個宣告的 writer。兩個就是黑板。"""
        flow = _flow(_tool("drafter", writes=["diff"]), _tool("patcher", writes=["diff"]))
        j = _joined(flow)
        self.assertIn("diff", j)
        self.assertIn("drafter", j)
        self.assertIn("patcher", j)

    def test_same_node_rewriting_on_revisit_is_not_a_conflict(self):
        """退回重訪時同一節點再寫同一欄位是合法覆寫——那正是退回邊的用途。"""
        flow = _flow(
            _tool("build", writes=["diff"]),
            {"id": "review", "branch": "$RUN/r.json", "reads": ["diff"],
             "cases": [{"when": {"path": "verdict", "op": "==", "value": "reject"},
                        "goto": "build", "back": True, "max_revisits": 2},
                       {"default": True, "goto": "accept"}]},
            _tool("accept"),
        )
        self.assertEqual(_problems(flow), [])


class BoundedCycles(unittest.TestCase):
    def _cycle(self, **case_extra):
        case = {"when": {"path": "verdict", "op": "==", "value": "reject"}, "goto": "build"}
        case.update(case_extra)
        return _flow(
            _tool("build", writes=["diff"]),
            {"id": "review", "branch": "$RUN/r.json",
             "cases": [case, {"default": True, "goto": "accept"}]},
            _tool("accept"),
        )

    def test_backward_goto_without_declaring_back_is_rejected(self):
        """舊的 forward-only 規則保留牙齒：沒宣告 back 就往後跳，仍然不准。"""
        j = _joined(self._cycle())
        self.assertIn("build", j)
        self.assertTrue("back" in j.lower() or "forward" in j.lower(), j)

    def test_back_edge_without_max_revisits_is_unbounded(self):
        j = _joined(self._cycle(back=True))
        self.assertIn("max_revisits", j)

    def test_back_edge_with_max_revisits_is_legal(self):
        self.assertEqual(_problems(self._cycle(back=True, max_revisits=2)), [])

    def test_max_revisits_must_be_a_positive_int(self):
        for bad in (0, -1, "two", 1.5):
            with self.subTest(bad=bad):
                self.assertNotEqual(_problems(self._cycle(back=True, max_revisits=bad)), [],
                                    f"max_revisits={bad!r} 應被拒")

    def test_back_true_on_a_forward_edge_is_a_declaration_lie(self):
        """宣告成退回邊卻指向前方 → 宣告說謊，且會讓環偵測被繞過。"""
        flow = _flow(
            _tool("a"),
            {"id": "b", "branch": "$RUN/r.json",
             "cases": [{"default": True, "goto": "c", "back": True, "max_revisits": 2}]},
            _tool("c"),
        )
        self.assertNotEqual(_problems(flow), [])

    def test_cycle_with_no_bounded_edge_anywhere_is_rejected(self):
        """兩條 branch 互跳形成的環，即使各自都「往前」也必須被抓到。"""
        flow = _flow(
            {"id": "p", "branch": "$RUN/r.json", "cases": [{"default": True, "goto": "q"}]},
            {"id": "q", "branch": "$RUN/r.json", "cases": [{"default": True, "goto": "p", "back": True}]},
        )
        self.assertNotEqual(_problems(flow), [])


class TopologyInfoForRenderingAndManifest(unittest.TestCase):
    """analyze() 的第二個回傳值餵給 --graph 與 manifest 的 topology 區塊。"""

    def test_info_lists_nodes_and_edges(self):
        flow = _flow(_tool("a", writes=["task"]), _tool("b", reads=["task"]))
        _, info = graph.analyze(flow)
        self.assertEqual([n["name"] for n in info["nodes"]], ["a", "b"])
        self.assertIn(("a", "b"), [(e["frm"], e["to"]) for e in info["edges"]])

    def test_info_records_field_ownership(self):
        flow = _flow(_tool("a", writes=["task"]), _tool("b", reads=["task"], writes=["diff"]))
        _, info = graph.analyze(flow)
        self.assertEqual(info["owners"], {"task": "a", "diff": "b"})

    def test_info_marks_back_edges_with_their_bound(self):
        flow = _flow(
            _tool("build", writes=["diff"]),
            {"id": "review", "branch": "$RUN/r.json",
             "cases": [{"when": {"path": "v", "op": "==", "value": "x"}, "goto": "build",
                        "back": True, "max_revisits": 3},
                       {"default": True, "goto": "accept"}]},
            _tool("accept"),
        )
        _, info = graph.analyze(flow)
        back = [e for e in info["edges"] if e.get("back")]
        self.assertEqual(len(back), 1)
        self.assertEqual((back[0]["frm"], back[0]["to"], back[0]["max_revisits"]),
                         ("review", "build", 3))


class FindingsCarryCodes(unittest.TestCase):
    """run.py 要能分辨「舊引擎本來就攔的」與「圖模型新增的」——靠 code，不靠比對字串。"""

    def _codes(self, flow):
        _, info = graph.analyze(flow)
        return [f["code"] for f in info["findings"]]

    def test_findings_pair_with_problem_messages(self):
        flow = _flow({"id": "b", "branch": "$RUN/a.json",
                      "cases": [{"default": True, "goto": "nope"}]})
        problems, info = graph.analyze(flow)
        self.assertEqual([f["message"] for f in info["findings"]], problems)

    def test_unknown_goto_code(self):
        flow = _flow({"id": "b", "branch": "$RUN/a.json",
                      "cases": [{"default": True, "goto": "nope"}]})
        self.assertIn("unknown_goto", self._codes(flow))

    def test_not_forward_only_code(self):
        flow = _flow(_tool("a"), {"id": "b", "branch": "$RUN/a.json",
                                  "cases": [{"default": True, "goto": "a"}]})
        self.assertIn("not_forward_only", self._codes(flow))

    def test_unreachable_code(self):
        flow = _flow({"id": "b", "branch": "$RUN/a.json",
                      "cases": [{"default": True, "goto": "end"}]},
                     _tool("orphan"), _tool("end"))
        self.assertIn("unreachable", self._codes(flow))

    def test_read_before_write_and_conflict_codes(self):
        self.assertIn("read_before_write",
                      self._codes(_flow(_tool("a"), _tool("b", reads=["x"]))))
        self.assertIn("write_conflict",
                      self._codes(_flow(_tool("a", writes=["x"]), _tool("b", writes=["x"]))))

    def test_back_edge_codes(self):
        flow = _flow(_tool("build"),
                     {"id": "review", "branch": "$RUN/r.json",
                      "cases": [{"default": True, "goto": "build", "back": True}]})
        self.assertIn("back_unbounded", self._codes(flow))


class ShippedFlowsPassTopologyAnalysis(unittest.TestCase):
    """既有出貨流程不得被新檢查誤判（回歸護欄的靜態版）。"""

    def test_every_shipped_flow_is_clean(self):
        import json
        paths = [os.path.join(KIT, "workflow", "flow.json")]
        ex = os.path.join(KIT, "workflow", "examples")
        paths += [os.path.join(ex, n) for n in sorted(os.listdir(ex)) if n.endswith(".json")]
        for p in paths:
            with self.subTest(flow=os.path.basename(p)):
                with open(p, encoding="utf-8") as f:
                    flow = json.load(f)
                self.assertEqual(_problems(flow), [], f"{os.path.basename(p)} 被誤判")


if __name__ == "__main__":
    unittest.main(verbosity=2)
