import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge.model import Finding, LintReport, PluginSpec

class TestModel(unittest.TestCase):
    def test_finding_fields(self):
        f = Finding(id="x", rule="manifest", severity="HARD", plugin="p", location="a.json", detail="bad")
        self.assertEqual(f.severity, "HARD")

    def test_report_clean_property(self):
        clean = LintReport(targets=["p"], hard=0, soft=2)
        dirty = LintReport(targets=["p"], hard=1, soft=0)
        self.assertTrue(clean.clean)
        self.assertFalse(dirty.clean)

    def test_pluginspec_defaults(self):
        s = PluginSpec(name="demo")
        self.assertEqual(s.pkg, "demo")           # pkg defaults to name without hyphens
        self.assertFalse(s.with_stop_hook)

    def test_pluginspec_pkg_strips_hyphens(self):
        self.assertEqual(PluginSpec(name="my-plugin").pkg, "myplugin")

    def test_pluginspec_pkg_sanitizes_dots_and_leading_digit(self):
        self.assertEqual(PluginSpec(name="my.plugin").pkg, "myplugin")
        self.assertEqual(PluginSpec(name="2cool").pkg, "_2cool")

if __name__ == "__main__":
    unittest.main()
