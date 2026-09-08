# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Unit tests：kit 終於掃自己的【待補】。

kit 的頭號鐵則是「缺值標【待補】、絕不臆造」，但改版前**kit 自己從不掃**：
alcoa-guard 掃必填欄位（不同 plugin、不同輸入），second-opinion 把它當合法佔位放行，
中間沒人檢查 kit 產出裡的殘留標記。

分工刻意保持與既有 hard/advisory 教條一致：
  • 宣告為必填的路徑仍是【待補】→ **硬失敗**（那是還沒做完的工作，不是誠實的空白）
  • 其他位置的【待補】→ 合法且應保留（那正是「不臆造」的正確做法），一律不阻擋
"""
import os
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "lib"))
import gates  # noqa: E402

M = "【待補】"


def _art(data):
    return {"schema": "t@1", "produced_by": "t", "data": data, "trace": []}


class RequiredFieldsAreHard(unittest.TestCase):
    def test_required_field_still_placeholder_fails(self):
        ok, reason = gates.run_gate("residual_gate", _art({"lot": M, "assay": 99.4}),
                                    {"required": ["lot"]})
        self.assertFalse(ok)
        self.assertIn("lot", reason)

    def test_required_field_filled_passes(self):
        ok, reason = gates.run_gate("residual_gate", _art({"lot": "A-123", "assay": 99.4}),
                                    {"required": ["lot"]})
        self.assertTrue(ok, reason)

    def test_required_field_embedded_placeholder_fails(self):
        """半填的字串也算沒填完："Lot 【待補】"。"""
        ok, _ = gates.run_gate("residual_gate", _art({"lot": f"Lot {M}"}), {"required": ["lot"]})
        self.assertFalse(ok)

    def test_missing_required_path_fails(self):
        """宣告必填卻整個欄位不存在 → 失敗（不得因為找不到就放行）。"""
        ok, reason = gates.run_gate("residual_gate", _art({"assay": 1}), {"required": ["lot"]})
        self.assertFalse(ok)
        self.assertIn("lot", reason)

    def test_dotted_path_into_nested_data(self):
        ok, _ = gates.run_gate("residual_gate", _art({"header": {"lot": M}}),
                               {"required": ["header.lot"]})
        self.assertFalse(ok)

    def test_required_list_entry_placeholder_fails(self):
        ok, _ = gates.run_gate("residual_gate", _art({"rows": ["a", M]}), {"required": ["rows"]})
        self.assertFalse(ok)


class ElsewherePlaceholdersAreLegitimate(unittest.TestCase):
    def test_placeholder_outside_required_fields_does_not_block(self):
        """未宣告必填處的【待補】是正確行為（誠實的空白），不得阻擋。"""
        ok, reason = gates.run_gate("residual_gate", _art({"lot": "A-1", "note": M}),
                                    {"required": ["lot"]})
        self.assertTrue(ok, reason)

    def test_no_args_never_blocks(self):
        ok, _ = gates.run_gate("residual_gate", _art({"anything": M}), {})
        self.assertTrue(ok)



class CustomMarker(unittest.TestCase):
    def test_marker_is_overridable(self):
        ok, _ = gates.run_gate("residual_gate", _art({"lot": "[TBD]"}),
                               {"required": ["lot"], "marker": "[TBD]"})
        self.assertFalse(ok)

    def test_default_marker_is_the_house_one(self):
        ok, _ = gates.run_gate("residual_gate", _art({"lot": "[TBD]"}), {"required": ["lot"]})
        self.assertTrue(ok, "預設只認【待補】；別的佔位符需明確宣告 marker")


class RegisteredWithTheOtherGates(unittest.TestCase):
    def test_gate_is_in_the_registry(self):
        self.assertIn("residual_gate", gates.REGISTRY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
