import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Record, IntegrityContract
from alcoaguard.rules import accurate

class TestAccurate(unittest.TestCase):
    def test_in_spec_ok(self):
        r = Record(fields={"result": 99.2})
        c = IntegrityContract(limits={"result": {"lo": 95.0, "hi": 105.0}})
        self.assertEqual(accurate.check(r, c, "HARD"), [])

    def test_out_of_spec(self):
        r = Record(fields={"result": 120.0})
        c = IntegrityContract(limits={"result": {"lo": 95.0, "hi": 105.0}})
        out = accurate.check(r, c, "HARD")
        self.assertTrue(any("out of spec" in f.detail for f in out))

    def test_aggregate_mismatch(self):
        r = Record(fields={"vals": [1, 2, 3]})
        c = IntegrityContract(aggregates=[{"op": "sum", "over": "vals", "stated": 7}])
        out = accurate.check(r, c, "SOFT")
        self.assertTrue(any("recomputed" in f.detail for f in out))

    def test_string_limit_does_not_crash(self):
        r = Record(fields={"result": 99.2})
        c = IntegrityContract(limits={"result": {"lo": "95", "hi": "105"}})
        self.assertEqual(accurate.check(r, c, "HARD"), [])

    def test_malformed_aggregate_skipped(self):
        r = Record(fields={"vals": [1, 2, 3]})
        c = IntegrityContract(aggregates=[{"op": "sum", "over": "vals"}])  # no 'stated'
        self.assertEqual(accurate.check(r, c, "SOFT"), [])

if __name__ == "__main__":
    unittest.main()
