import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge.model import LintReport, Finding
from pluginforge import report

class TestReport(unittest.TestCase):
    def _rep(self):
        return LintReport(targets=["a"], hard=1, soft=1, findings=[
            Finding("i1", "manifest", "HARD", "a", "plugin.json", "missing name/version"),
            Finding("i2", "manifest", "SOFT", "a", "plugin.json", "recommended field missing: keywords")])

    def test_build_marks_clean_false(self):
        r = report.build(self._rep())
        self.assertFalse(r["clean"])
        self.assertEqual(r["summary"]["hard"], 1)

    def test_markdown_sections(self):
        md = report.to_markdown(report.build(self._rep()))
        self.assertIn("HARD", md)
        self.assertIn("missing name/version", md)
        self.assertIn("keywords", md)

    def test_write_two_files(self):
        with tempfile.TemporaryDirectory() as d:
            j, m = report.write(report.build(self._rep()), d)
            self.assertTrue(os.path.exists(j) and os.path.exists(m))
            with open(j, encoding="utf-8") as f:
                json.load(f)

if __name__ == "__main__":
    unittest.main()
