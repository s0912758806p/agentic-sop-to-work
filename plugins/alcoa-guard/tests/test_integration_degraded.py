import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard import review

CSV = ("field,value,author,timestamp\n"
       "performed,2026-05-02,Alice,2026-05-02T09:00:00\n"
       "signed,2026-05-01,Bob,2026-05-01T09:00:00\n")  # signed before performed -> violation
CONTRACT = {"date_fields": ["performed", "signed"], "date_order": [["performed", "signed"]]}

class TestDegraded(unittest.TestCase):
    def test_backdating_flagged_soft(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            rp = os.path.join(d, "e.csv"); open(rp, "w", encoding="utf-8").write(CSV)
            cp = os.path.join(d, ".alcoa.json"); json.dump(CONTRACT, open(cp, "w", encoding="utf-8"))
            rep, jpath, mpath = review.run_degraded(rp, cp, out_base=os.path.join(d, "out"),
                                                    as_of=__import__("datetime").date(2026, 6, 1))
            self.assertEqual(rep["summary"]["soft"], 1)
            self.assertTrue(os.path.exists(mpath))

if __name__ == "__main__":
    unittest.main()
