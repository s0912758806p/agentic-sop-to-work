# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Test export_claude_skill.py — runner skills written into a temp project (no side effects)."""
import os
import sys
import tempfile
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIT)
import export_claude_skill as ex  # noqa: E402


class Export(unittest.TestCase):
    def test_export_extract_runner(self):
        with tempfile.TemporaryDirectory() as d:
            out = ex.export_one("extract", project=d)
            self.assertTrue(os.path.exists(out))
            txt = open(out, encoding="utf-8").read()
            self.assertTrue(txt.startswith("---\nname: extract\n"), "frontmatter name")
            self.assertIn("description:", txt)
            # runner contract: it must tell Claude to RUN the deterministic tool, not redo it in-context
            self.assertIn("tool.py", txt)
            self.assertIn("DRAFT", txt)
            self.assertIn(os.path.join(".claude", "skills", "extract"), out)

    def test_all_uses_registry(self):
        with tempfile.TemporaryDirectory() as d:
            ex.main(["--all", "--project", d])
            for n in ("extract", "compute", "report"):
                self.assertTrue(
                    os.path.exists(os.path.join(d, ".claude", "skills", n, "SKILL.md")),
                    f"{n} runner skill should be generated")

    def test_remove_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            ex.export_one("extract", project=d)
            path = os.path.join(d, ".claude", "skills", "extract", "SKILL.md")
            self.assertTrue(os.path.exists(path))
            self.assertTrue(ex.remove_one("extract", project=d))
            self.assertFalse(os.path.exists(path))
            # idempotent: removing again is a no-op (returns False), not an error
            self.assertFalse(ex.remove_one("extract", project=d))

    def test_remove_refuses_foreign_skill(self):
        # a hand-written skill (no generated marker) must NOT be deleted without --force
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, ".claude", "skills", "mine")
            os.makedirs(p)
            with open(os.path.join(p, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("---\nname: mine\ndescription: hand-written\n---\nmine\n")
            self.assertFalse(ex.remove_one("mine", project=d))               # refused
            self.assertTrue(os.path.exists(os.path.join(p, "SKILL.md")))     # untouched
            self.assertTrue(ex.remove_one("mine", project=d, force=True))    # --force overrides
            self.assertFalse(os.path.exists(os.path.join(p, "SKILL.md")))


if __name__ == "__main__":
    unittest.main()
