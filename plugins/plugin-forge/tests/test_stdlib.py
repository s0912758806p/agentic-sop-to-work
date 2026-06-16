import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge.rules import stdlib

def _pkg(d, pkg, body):
    os.makedirs(os.path.join(d, pkg), exist_ok=True)
    with open(os.path.join(d, pkg, "__init__.py"), "w") as _f:
        pass
    with open(os.path.join(d, pkg, "m.py"), "w", encoding="utf-8") as f:
        f.write(body)

class TestStdlib(unittest.TestCase):
    def test_not_strict_is_noop(self):
        with tempfile.TemporaryDirectory() as d:
            _pkg(d, "demo", "import requests\n")
            self.assertEqual(stdlib.check(d, strict=False), [])

    def test_stdlib_only_passes(self):
        with tempfile.TemporaryDirectory() as d:
            _pkg(d, "demo", "import os, json\nfrom .m2 import x\n")
            self.assertEqual(stdlib.check(d, strict=True), [])

    def test_third_party_import_is_hard(self):
        with tempfile.TemporaryDirectory() as d:
            _pkg(d, "demo", "import requests\n")
            out = stdlib.check(d, strict=True)
            self.assertTrue(any(f.severity == "HARD" and "requests" in f.detail for f in out))

    def test_intra_plugin_import_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            _pkg(d, "demo", "import demo\nfrom demo import m\n")
            self.assertEqual(stdlib.check(d, strict=True), [])

    def test_tests_and_examples_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            with open(os.path.join(d, "tests", "test_x.py"), "w", encoding="utf-8") as f:
                f.write("import pytest\n")  # third-party in tests/ must be ignored
            self.assertEqual(stdlib.check(d, strict=True), [])

    def test_common_stdlib_modules_recognized(self):
        # regression: fallback (Python <3.10) must cover common stdlib, not just a handful
        with tempfile.TemporaryDirectory() as d:
            _pkg(d, "demo", "import time, shutil, statistics, uuid, importlib\n")
            self.assertEqual(stdlib.check(d, strict=True), [])

if __name__ == "__main__":
    unittest.main()
