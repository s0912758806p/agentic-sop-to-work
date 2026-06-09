# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Test new_skill.py scaffolding — runs in an isolated temp root, never touches the real kit."""
import json
import os
import shutil
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
import new_skill  # noqa: E402


class NewSkill(unittest.TestCase):
    def test_scaffold_isolated(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(os.path.join(KIT, "templates", "skill_template"),
                            os.path.join(d, "templates", "skill_template"))
            os.makedirs(os.path.join(d, "skills"))
            os.makedirs(os.path.join(d, "tests", "unit"))
            with open(os.path.join(d, "tests", "registry.json"), "w", encoding="utf-8") as f:
                json.dump({"version": 1, "skills": {}, "integration": {"tests": []}}, f)

            new_skill.create("myskill", force=False, root=d)

            self.assertTrue(os.path.exists(os.path.join(d, "skills", "myskill", "tool.py")))
            self.assertTrue(os.path.exists(os.path.join(d, "skills", "myskill", "SKILL.md")))
            self.assertTrue(os.path.exists(os.path.join(d, "tests", "unit", "test_myskill.py")))
            tool = open(os.path.join(d, "skills", "myskill", "tool.py"), encoding="utf-8").read()
            self.assertIn('WHO = "myskill"', tool)
            self.assertNotIn("<skill-name>", tool)
            reg = json.load(open(os.path.join(d, "tests", "registry.json"), encoding="utf-8"))
            self.assertIn("myskill", reg["skills"])
            self.assertEqual(reg["skills"]["myskill"]["tests"], ["tests/unit/test_myskill.py"])

    def test_rejects_bad_name(self):
        with self.assertRaises(SystemExit):
            new_skill.create("1bad name", root=tempfile.gettempdir())


if __name__ == "__main__":
    unittest.main()
