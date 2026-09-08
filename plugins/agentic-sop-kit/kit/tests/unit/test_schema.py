# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Unit tests：把交接邊變成**有型別的契約**。

改版前 `artifact["schema"]` 是裝飾品——`kit.artifact()` 不驗證，`schema_gate` 從不讀它，
`readings@1` 只在一支測試裡被斷言過。在線性管線那是技術債；在圖裡「邊沒有型別」
等於交接協定是假的。這支測試釘住「schema tag 有牙齒」。

向後相容是硬要求：`schema_gate` 沒給 `schema_ref` 時，行為必須與改版前逐字相同
（既有 `be.json` 用的就是那條路徑）。
"""
import json
import os
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "lib"))
import gates  # noqa: E402
import schema  # noqa: E402


def _mkregistry(*decls):
    """Write schema declaration files to a temp dir and load them back."""
    d = tempfile.mkdtemp()
    for decl in decls:
        with open(os.path.join(d, decl["schema"].replace("@", "_") + ".json"), "w", encoding="utf-8") as f:
            json.dump(decl, f)
    return d, schema.load_registry(d)


READINGS = {"schema": "readings@1",
            "required": ["readings", "skipped"],
            "types": {"readings": "list", "skipped": "list"}}
STATS = {"schema": "stats@1",
         "required": ["stats"],
         "types": {"stats": "dict"}}


def _art(tag, data, trace=None):
    return {"schema": tag, "produced_by": "t", "data": data, "trace": trace or []}


class LoadRegistry(unittest.TestCase):
    def test_keys_by_declared_tag_not_filename(self):
        d, reg = _mkregistry(READINGS, STATS)
        self.assertEqual(set(reg), {"readings@1", "stats@1"})

    def test_missing_dir_is_empty_registry_not_a_crash(self):
        self.assertEqual(schema.load_registry(os.path.join(tempfile.mkdtemp(), "nope")), {})


class Validate(unittest.TestCase):
    def setUp(self):
        _, self.reg = _mkregistry(READINGS, STATS)

    def test_conforming_artifact_passes(self):
        ok, reason = schema.validate(_art("readings@1", {"readings": [], "skipped": []}), self.reg)
        self.assertTrue(ok, reason)

    def test_tag_mismatch_names_both_sides(self):
        art = _art("stats@1", {"stats": {}})
        ok, reason = schema.validate(art, self.reg, expected="readings@1")
        self.assertFalse(ok)
        self.assertIn("readings@1", reason)
        self.assertIn("stats@1", reason)

    def test_missing_required_field_names_the_field(self):
        ok, reason = schema.validate(_art("readings@1", {"readings": []}), self.reg)
        self.assertFalse(ok)
        self.assertIn("skipped", reason)

    def test_wrong_type_names_field_and_expected_type(self):
        ok, reason = schema.validate(_art("readings@1", {"readings": {}, "skipped": []}), self.reg)
        self.assertFalse(ok)
        self.assertIn("readings", reason)
        self.assertIn("list", reason)

    def test_unknown_tag_is_a_failure_not_a_pass(self):
        """未註冊的 tag 不得放行——否則打錯字就靜默繞過型別檢查。"""
        ok, reason = schema.validate(_art("readings@99", {"readings": [], "skipped": []}), self.reg)
        self.assertFalse(ok)
        self.assertIn("readings@99", reason)

    def test_artifact_without_schema_tag_fails(self):
        ok, reason = schema.validate({"data": {"readings": [], "skipped": []}}, self.reg)
        self.assertFalse(ok)
        self.assertIn("schema", reason)

    def test_number_type_accepts_int_and_float_rejects_str(self):
        _, reg = _mkregistry({"schema": "n@1", "required": ["v"], "types": {"v": "number"}})
        self.assertTrue(schema.validate(_art("n@1", {"v": 1}), reg)[0])
        self.assertTrue(schema.validate(_art("n@1", {"v": 1.5}), reg)[0])
        self.assertFalse(schema.validate(_art("n@1", {"v": "1"}), reg)[0])

    def test_bool_is_not_a_number(self):
        """Python 的 bool 是 int 的子類；型別檢查不得把 True 當數字放行。"""
        _, reg = _mkregistry({"schema": "n@1", "required": ["v"], "types": {"v": "number"}})
        self.assertFalse(schema.validate(_art("n@1", {"v": True}), reg)[0])


class SchemaGateBackwardCompatible(unittest.TestCase):
    """沒給 schema_ref → 行為與改版前逐字相同（be.json 走這條）。"""

    def test_required_only_still_passes(self):
        ok, _ = gates.run_gate("schema_gate", {"data": {"id": 1, "name": "x"}},
                               {"required": ["id", "name"]})
        self.assertTrue(ok)

    def test_required_only_still_fails_and_lists_missing(self):
        ok, reason = gates.run_gate("schema_gate", {"data": {"id": 1}}, {"required": ["id", "name"]})
        self.assertFalse(ok)
        self.assertIn("name", reason)

    def test_no_args_passes_untagged_artifact(self):
        """改版前 schema_gate({} ) 對任何 artifact 都放行——不得因新功能變嚴。"""
        ok, _ = gates.run_gate("schema_gate", {"data": {"anything": 1}}, {})
        self.assertTrue(ok)


class SchemaGateTypedEdge(unittest.TestCase):
    """給了 schema_ref → 驗 tag ＋ 驗形狀。"""

    def setUp(self):
        self.dir, _ = _mkregistry(READINGS, STATS)

    def test_declared_ref_matching_artifact_passes(self):
        art = _art("readings@1", {"readings": [], "skipped": []})
        ok, reason = gates.run_gate("schema_gate", art,
                                    {"schema_ref": "readings@1", "schema_dir": self.dir})
        self.assertTrue(ok, reason)

    def test_wrong_tag_on_the_edge_fails(self):
        """上游送了 stats@1 到一條宣告 readings@1 的邊上 → 硬失敗。"""
        art = _art("stats@1", {"stats": {}})
        ok, reason = gates.run_gate("schema_gate", art,
                                    {"schema_ref": "readings@1", "schema_dir": self.dir})
        self.assertFalse(ok)
        self.assertIn("readings@1", reason)

    def test_right_tag_but_malformed_data_fails(self):
        art = _art("readings@1", {"readings": "not-a-list", "skipped": []})
        ok, reason = gates.run_gate("schema_gate", art,
                                    {"schema_ref": "readings@1", "schema_dir": self.dir})
        self.assertFalse(ok)
        self.assertIn("list", reason)

    def test_required_and_schema_ref_both_enforced(self):
        art = _art("readings@1", {"readings": [], "skipped": []})
        ok, reason = gates.run_gate("schema_gate", art,
                                    {"schema_ref": "readings@1", "schema_dir": self.dir,
                                     "required": ["readings", "extra"]})
        self.assertFalse(ok, "required 仍須被檢查")
        self.assertIn("extra", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
