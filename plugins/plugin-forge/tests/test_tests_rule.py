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
            ids = {f.location for f in out}
            self.assertIn("tests/verify.py", ids)
            self.assertIn("tests/test_no_third_party.py", ids)
            self.assertTrue(all(f.severity == "HARD" for f in out))

    def test_present_harness_passes(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tests"))
            for fn in ("verify.py", "test_no_third_party.py"):
                with open(os.path.join(d, "tests", fn), "w") as _f:
                    pass
            self.assertEqual(tests_rule.check(d, strict=True), [])

if __name__ == "__main__":
    unittest.main()
