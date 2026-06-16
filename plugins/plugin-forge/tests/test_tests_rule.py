import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge.rules import tests as tests_rule

class TestTestsRule(unittest.TestCase):
    def test_not_strict_noop(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(tests_rule.check(d, strict=False), [])

    def test_missing_harness_is_hard(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            out = tests_rule.check(d, strict=True)
            details = " ".join(f.detail for f in out)
            self.assertIn("verify.py", details)
            self.assertIn("test_no_third_party.py", details)
            self.assertTrue(out and all(f.severity == "HARD" for f in out))

    def test_nested_harness_passes(self):
        # kit-style: harness under a nested subdir, not top-level tests/
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "kit", "tests"))
            for fn in ("verify.py", "test_no_third_party.py"):
                with open(os.path.join(d, "kit", "tests", fn), "w") as f:
                    pass
            self.assertEqual(tests_rule.check(d, strict=True), [])

    def test_harness_in_examples_does_not_count(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "examples"))
            for fn in ("verify.py", "test_no_third_party.py"):
                with open(os.path.join(d, "examples", fn), "w") as f:
                    pass
            self.assertEqual(len(tests_rule.check(d, strict=True)), 2)

    def test_present_harness_passes(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            for fn in ("verify.py", "test_no_third_party.py"):
                with open(os.path.join(d, "tests", fn), "w") as _f:
                    pass
            self.assertEqual(tests_rule.check(d, strict=True), [])

if __name__ == "__main__":
    unittest.main()
