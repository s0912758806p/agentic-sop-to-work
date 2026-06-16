import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge import checks

def _good_plugin(root, name="a"):
    pd = os.path.join(root, "plugins", name)
    os.makedirs(os.path.join(pd, ".claude-plugin"))
    with open(os.path.join(pd, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "version": "0.1.0"}, f)
    return pd

class TestChecks(unittest.TestCase):
    def test_single_plugin_clean(self):
        with tempfile.TemporaryDirectory() as d:
            pd = _good_plugin(d)
            rep = checks.run_lint(plugin_dir=pd, strict=False)
            self.assertTrue(rep.clean)
            self.assertEqual(rep.targets, ["a"])

    def test_all_flags_marketplace_problem(self):
        with tempfile.TemporaryDirectory() as d:
            _good_plugin(d, "a")
            os.makedirs(os.path.join(d, ".claude-plugin"))
            with open(os.path.join(d, ".claude-plugin", "marketplace.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "mp", "plugins": [
                    {"name": "a", "source": "./plugins/a"},
                    {"name": "ghost", "source": "./plugins/ghost"}]}, f)  # ghost has no plugin.json
            rep = checks.run_lint(repo_root=d, all_plugins=True, strict=False)
            self.assertFalse(rep.clean)
            self.assertTrue(any("ghost" in f.detail or f.plugin == "ghost" for f in rep.findings))

if __name__ == "__main__":
    unittest.main()
