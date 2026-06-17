import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge import scaffold, checks
from pluginforge.model import PluginSpec

class TestScaffoldPassesLint(unittest.TestCase):
    def test_scaffolded_plugin_is_strict_clean(self):
        with tempfile.TemporaryDirectory() as d:
            pdir = scaffold.generate(PluginSpec(name="demo-plugin"), dest_root=d)
            self.assertTrue(os.path.exists(os.path.join(pdir, ".claude-plugin", "plugin.json")))
            rep = checks.run_lint(plugin_dir=pdir, strict=True)
            self.assertTrue(rep.clean, "scaffold output must pass lint --strict; findings: "
                            + "; ".join(f.detail for f in rep.findings))

    def test_scaffold_creates_required_harness(self):
        with tempfile.TemporaryDirectory() as d:
            pdir = scaffold.generate(PluginSpec(name="demo2"), dest_root=d)
            for rel in ("tests/verify.py", "tests/test_no_third_party.py",
                        "skills/demo2/SKILL.md", "commands/demo2.md",
                        "hooks/hooks.json", "hooks/session_check.py", "demo2/__init__.py"):
                self.assertTrue(os.path.exists(os.path.join(pdir, rel)), f"missing {rel}")

if __name__ == "__main__":
    unittest.main()
