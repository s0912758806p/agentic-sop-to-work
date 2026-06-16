import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Verdict, Finding
from alcoaguard import report

class TestReport(unittest.TestCase):
    def _verdict(self):
        return Verdict(mode="FULL", hard=1, soft=0, human_items=2,
                       findings=[Finding(id="x", principle="complete", severity="HARD",
                                         origin="deterministic", location="a", detail="blank")],
                       checklist=["confirm authorized", "confirm justified"])

    def test_build_freezes_verdict(self):
        rep = report.build(self._verdict())
        self.assertEqual(rep["verdict"], "ADVISORY_ONLY")
        self.assertTrue(rep["human_owns_verdict"])
        self.assertEqual(rep["summary"]["hard"], 1)

    def test_markdown_shows_checklist_and_caveat(self):
        md = report.to_markdown(report.build(self._verdict()))
        self.assertIn("DRAFT", md)
        self.assertIn("does NOT mean fully compliant", md)
        self.assertIn("confirm authorized", md)

    def test_write_emits_two_files(self):
        with tempfile.TemporaryDirectory() as d:
            j, m = report.write(report.build(self._verdict()), d)
            self.assertTrue(os.path.exists(j) and os.path.exists(m))
            json.load(open(j, encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
