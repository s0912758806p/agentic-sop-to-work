import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Entry, Record, IntegrityContract, Finding, Verdict

class TestModel(unittest.TestCase):
    def test_record_defaults(self):
        r = Record()
        self.assertEqual(r.mode, "DEGRADED")
        self.assertEqual(r.fields, {})
        self.assertEqual(r.entries, [])

    def test_entry_attribution_fields(self):
        e = Entry(field="result", value="99.2", author="Alice", timestamp="2026-05-01T09:00:00")
        self.assertEqual(e.author, "Alice")
        self.assertEqual(e.kind, "text")

    def test_contract_defaults_are_empty(self):
        c = IntegrityContract()
        self.assertEqual(c.required_fields, [])
        self.assertFalse(c.no_future)

    def test_verdict_human_owns(self):
        v = Verdict(mode="FULL", hard=1, soft=0, human_items=4)
        self.assertTrue(v.human_owns_verdict)

if __name__ == "__main__":
    unittest.main()
