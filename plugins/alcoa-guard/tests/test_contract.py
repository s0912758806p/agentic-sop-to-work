import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard import contract as C

class TestContract(unittest.TestCase):
    def test_from_dict_maps_fields(self):
        c = C.from_dict({"required_fields": ["a"], "no_future": True,
                         "date_order": [["p", "s"]]})
        self.assertEqual(c.required_fields, ["a"])
        self.assertTrue(c.no_future)
        self.assertEqual(c.date_order, [["p", "s"]])

    def test_load_reads_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, ".alcoa.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"required_fields": ["x"]}, f)
            c = C.load(p)
            self.assertEqual(c.required_fields, ["x"])

    def test_infer_only_unambiguous(self):
        run_data = {"data": {"aggregates": [{"op": "mean", "over": "vals", "stated": 2.0}],
                             "results": [{"id": "S1"}, {"id": "S2"}]}}
        c = C.infer_from_run(run_data)
        self.assertEqual(len(c.aggregates), 1)
        self.assertEqual(c.expected_set["results"], ["S1", "S2"])
        # inference must NOT invent required_fields/attribution
        self.assertEqual(c.required_fields, [])
        self.assertEqual(c.attribution, [])

if __name__ == "__main__":
    unittest.main()
