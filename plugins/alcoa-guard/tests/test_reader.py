import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard import reader

CSV = ("field,value,author,timestamp,kind\n"
       "operator,Alice,Alice,2026-05-01T09:00:00,text\n"
       "result,99.2,Alice,2026-05-01T09:30:00,number\n")

class TestReader(unittest.TestCase):
    def test_csv_to_record(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "entries.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write(CSV)
            r = reader.read_degraded(p, None)
            self.assertEqual(r.mode, "DEGRADED")
            self.assertEqual(r.fields["result"], "99.2")
            self.assertEqual(len(r.entries), 2)
            self.assertEqual(r.entries[0].author, "Alice")

    def test_json_to_record(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rec.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"fields": {"a": 1}, "entries": []}, f)
            r = reader.read_degraded(p, None)
            self.assertEqual(r.fields["a"], 1)

    def test_json_list_root_is_empty_record(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rec.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump([1, 2, 3], f)   # list at root, not a dict
            r = reader.read_degraded(p, None)
            self.assertEqual(r.fields, {})
            self.assertEqual(r.entries, [])

    def test_read_full_loads_last_json_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            art = os.path.join(d, "b.stats.json")
            with open(art, "w", encoding="utf-8") as f:
                json.dump({"data": {"vals": [1, 2, 3]}}, f)
            man = os.path.join(d, "run_manifest.json")
            with open(man, "w", encoding="utf-8") as f:
                json.dump({"steps": [{"skill": "compute", "out": art}], "final_output": art}, f)
            rec, run_data = reader.read_full(d)
            self.assertEqual(rec.mode, "FULL")
            self.assertEqual(rec.fields["vals"], [1, 2, 3])
            self.assertEqual(run_data["data"]["vals"], [1, 2, 3])

if __name__ == "__main__":
    unittest.main()
