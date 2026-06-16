import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge.rules import manifest

def _plugin(d, name="p", version="0.1.0"):
    os.makedirs(os.path.join(d, ".claude-plugin"), exist_ok=True)
    obj = {}
    if name is not None: obj["name"] = name
    if version is not None: obj["version"] = version
    with open(os.path.join(d, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return d

class TestManifest(unittest.TestCase):
    def test_plugin_manifest_ok(self):
        with tempfile.TemporaryDirectory() as d:
            _plugin(d)
            self.assertEqual(manifest.check_plugin_manifest(d, strict=False), [])

    def test_plugin_manifest_missing_version(self):
        with tempfile.TemporaryDirectory() as d:
            _plugin(d, version=None)
            out = manifest.check_plugin_manifest(d, strict=False)
            self.assertTrue(any(f.severity == "HARD" and "name/version" in f.detail for f in out))

    def test_strict_warns_recommended_fields(self):
        with tempfile.TemporaryDirectory() as d:
            _plugin(d)  # no author/license/keywords
            out = manifest.check_plugin_manifest(d, strict=True)
            self.assertTrue(any(f.severity == "SOFT" and "author" in f.detail for f in out))
            self.assertFalse(any(f.severity == "HARD" for f in out))

    def test_marketplace_missing_pluginjson(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude-plugin"))
            with open(os.path.join(d, ".claude-plugin", "marketplace.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "mp", "plugins": [{"name": "a", "source": "./plugins/a"}]}, f)
            out = manifest.check_marketplace(d)  # plugins/a/.claude-plugin/plugin.json absent
            self.assertTrue(any("missing" in f.detail and "plugin.json" in f.detail for f in out))

    def test_multiple_bad_entries_get_distinct_ids(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude-plugin"))
            with open(os.path.join(d, ".claude-plugin", "marketplace.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "mp", "plugins": [{"source": "./a"}, {"source": "./b"}]}, f)
            out = manifest.check_marketplace(d)
            ids = {x.id for x in out if x.id.startswith("manifest:entry:")}
            self.assertEqual(len(ids), 2)

if __name__ == "__main__":
    unittest.main()
