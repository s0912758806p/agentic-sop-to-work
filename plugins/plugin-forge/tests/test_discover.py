import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge import discover

class TestDiscover(unittest.TestCase):
    def _repo(self, d):
        os.makedirs(os.path.join(d, ".claude-plugin"))
        with open(os.path.join(d, ".claude-plugin", "marketplace.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "mp", "plugins": [
                {"name": "a", "source": "./plugins/a"},
                {"name": "b", "source": "./plugins/b"}]}, f)
        return d

    def test_from_marketplace(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            got = discover.from_marketplace(d)
            names = [n for n, _ in got]
            self.assertEqual(names, ["a", "b"])
            self.assertTrue(got[0][1].endswith(os.path.join("plugins", "a")))

    def test_plugin_name_from_pluginjson(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude-plugin"))
            with open(os.path.join(d, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "cool", "version": "0.1.0"}, f)
            self.assertEqual(discover.plugin_name(d), "cool")

    def test_plugin_name_fallback_to_dirname(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(discover.plugin_name(os.path.join(d, "fallbackname")), "fallbackname")

if __name__ == "__main__":
    unittest.main()
