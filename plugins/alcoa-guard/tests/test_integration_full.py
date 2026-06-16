import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard import review

class TestFull(unittest.TestCase):
    def _make_run(self, d):
        art = os.path.join(d, "b.stats.json")
        with open(art, "w", encoding="utf-8") as fh:
            json.dump({"produced_by": "compute", "data": {"vals": [1, 2, 3],
                      "aggregates": [{"op": "sum", "over": "vals", "stated": 99}]}}, fh)
        man = os.path.join(d, "run_manifest.json")
        with open(man, "w", encoding="utf-8") as fh:
            json.dump({"flow": "f", "run_id": "r", "steps": [{"skill": "compute", "out": art}],
                       "final_output": art}, fh)
        return d

    def test_full_infers_and_flags_hard(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_run(d)
            rep, jpath, mpath = review.run_full(d, out_base=os.path.join(d, "out"),
                                                as_of=__import__("datetime").date(2026, 6, 1))
            self.assertEqual(rep["mode"], "FULL")
            self.assertEqual(rep["summary"]["hard"], 1)   # sum stated 99 != 6

    def test_full_results_path_does_not_crash(self):
        import datetime
        with tempfile.TemporaryDirectory() as d:
            art = os.path.join(d, "b.stats.json")
            with open(art, "w", encoding="utf-8") as fh:
                json.dump({"data": {"results": [{"id": "S1"}, {"id": "S2"}]}}, fh)
            man = os.path.join(d, "run_manifest.json")
            with open(man, "w", encoding="utf-8") as fh:
                json.dump({"steps": [{"skill": "compute", "out": art}],
                           "final_output": art}, fh)
            rep, jpath, mpath = review.run_full(
                d, out_base=os.path.join(d, "out"), as_of=datetime.date(2026, 6, 1))
            self.assertEqual(rep["mode"], "FULL")
            # inferred expected_set == present ids -> zero completeness findings, no crash
            self.assertEqual([f for f in rep["findings"] if f["principle"] == "complete"], [])

if __name__ == "__main__":
    unittest.main()
