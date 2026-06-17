import os, sys, json, tempfile, subprocess, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pluginforge", "lint.py")

def _good(root, name="a"):
    pd = os.path.join(root, "plugins", name)
    os.makedirs(os.path.join(pd, ".claude-plugin"))
    with open(os.path.join(pd, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "version": "0.1.0"}, f)
    return pd

class TestLintCLI(unittest.TestCase):
    def test_clean_plugin_exit0(self):
        with tempfile.TemporaryDirectory() as d:
            pd = _good(d)
            r = subprocess.run([sys.executable, LINT, pd], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("CLEAN", r.stdout)

    def test_bad_plugin_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            pd = os.path.join(d, "plugins", "b")
            os.makedirs(os.path.join(pd, ".claude-plugin"))
            with open(os.path.join(pd, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "b"}, f)  # missing version -> HARD
            r = subprocess.run([sys.executable, LINT, pd], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("name/version", r.stdout)

    def test_no_args_errors(self):
        r = subprocess.run([sys.executable, LINT], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)  # argparse usage error, not a crash (1)

    def test_good_example_clean_bad_example_fails(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        good = os.path.join(base, "pluginforge", "examples", "good_plugin")
        bad = os.path.join(base, "pluginforge", "examples", "bad_plugin")
        rg = subprocess.run([sys.executable, LINT, good, "--strict"], capture_output=True, text=True)
        self.assertEqual(rg.returncode, 0, rg.stdout)
        rb = subprocess.run([sys.executable, LINT, bad, "--strict"], capture_output=True, text=True)
        self.assertEqual(rb.returncode, 1)
        self.assertIn("requests", rb.stdout)  # stdlib rule caught the third-party import

if __name__ == "__main__":
    unittest.main()
