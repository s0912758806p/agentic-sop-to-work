import os, sys, unittest
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Record, Entry, IntegrityContract
from alcoaguard import checks

class TestChecks(unittest.TestCase):
    def test_full_is_hard_degraded_is_soft(self):
        r_full = Record(fields={"a": ""}, mode="FULL")
        r_deg = Record(fields={"a": ""}, mode="DEGRADED")
        c = IntegrityContract(required_fields=["a"])
        self.assertEqual(checks.run_rules(r_full, c, as_of=date(2026, 6, 1)).hard, 1)
        self.assertEqual(checks.run_rules(r_deg, c, as_of=date(2026, 6, 1)).soft, 1)

    def test_clean_record_no_findings_but_has_checklist(self):
        r = Record(fields={"a": "x"}, mode="FULL")
        c = IntegrityContract(required_fields=["a"])
        v = checks.run_rules(r, c, as_of=date(2026, 6, 1))
        self.assertEqual(v.hard, 0)
        self.assertGreater(v.human_items, 0)   # GREEN still ships a human checklist

    def test_only_filter(self):
        r = Record(fields={"a": ""}, mode="FULL")
        c = IntegrityContract(required_fields=["a"])
        v = checks.run_rules(r, c, as_of=date(2026, 6, 1), only={"accurate"})
        self.assertEqual(v.hard, 0)   # complete rule skipped

if __name__ == "__main__":
    unittest.main()
