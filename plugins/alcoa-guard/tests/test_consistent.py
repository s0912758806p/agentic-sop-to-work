import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Record, IntegrityContract
from alcoaguard.rules import consistent

class TestConsistent(unittest.TestCase):
    def test_id_pattern_ok(self):
        r = Record(fields={"lot": "LOT-2026-001"})
        c = IntegrityContract(id_patterns={"lot": r"LOT-\d{4}-\d{3}"})
        self.assertEqual(consistent.check(r, c, "HARD"), [])

    def test_id_pattern_violation(self):
        r = Record(fields={"lot": "bad"})
        c = IntegrityContract(id_patterns={"lot": r"LOT-\d{4}-\d{3}"})
        out = consistent.check(r, c, "HARD")
        self.assertTrue(any("pattern" in f.detail for f in out))

    def test_unit_missing(self):
        r = Record(fields={"mass": "500"})
        c = IntegrityContract(units={"mass": "mg"})
        out = consistent.check(r, c, "SOFT")
        self.assertTrue(any("unit" in f.detail for f in out))

if __name__ == "__main__":
    unittest.main()
