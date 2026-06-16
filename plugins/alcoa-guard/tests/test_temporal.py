import os, sys, unittest
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Record, IntegrityContract
from alcoaguard.rules import temporal

class TestTemporal(unittest.TestCase):
    def test_order_ok(self):
        r = Record(fields={"performed": "2026-05-01", "signed": "2026-05-02"})
        c = IntegrityContract(date_fields=["performed", "signed"], date_order=[["performed", "signed"]])
        self.assertEqual(temporal.check(r, c, "HARD", as_of=date(2026, 6, 1)), [])

    def test_backdating_caught(self):
        r = Record(fields={"performed": "2026-05-02", "signed": "2026-05-01"})
        c = IntegrityContract(date_fields=["performed", "signed"], date_order=[["performed", "signed"]])
        out = temporal.check(r, c, "HARD", as_of=date(2026, 6, 1))
        self.assertTrue(any("after" in f.detail for f in out))

    def test_future_date(self):
        r = Record(fields={"performed": "2027-01-01"})
        c = IntegrityContract(date_fields=["performed"], no_future=True)
        out = temporal.check(r, c, "HARD", as_of=date(2026, 6, 1))
        self.assertTrue(any("future" in f.detail for f in out))

    def test_unparseable_date(self):
        r = Record(fields={"performed": "not-a-date"})
        c = IntegrityContract(date_fields=["performed"])
        out = temporal.check(r, c, "SOFT", as_of=date(2026, 6, 1))
        self.assertTrue(any("unparseable" in f.detail for f in out))

if __name__ == "__main__":
    unittest.main()
