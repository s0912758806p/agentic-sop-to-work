import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Record, Entry, IntegrityContract
from alcoaguard.rules import attributable

class TestAttributable(unittest.TestCase):
    def _rec(self, author, ts):
        return Record(entries=[Entry(field="result", value="9", author=author, timestamp=ts)],
                      fields={"result": "9"})

    def test_ok_when_attributed(self):
        c = IntegrityContract(attribution=["result"])
        self.assertEqual(attributable.check(self._rec("Alice", "2026-05-01"), c, "HARD"), [])

    def test_missing_author(self):
        c = IntegrityContract(attribution=["result"])
        out = attributable.check(self._rec(None, "2026-05-01"), c, "HARD")
        self.assertTrue(any("author" in f.detail for f in out))
        self.assertEqual(out[0].severity, "HARD")

    def test_field_with_no_entry(self):
        c = IntegrityContract(attribution=["missing"])
        out = attributable.check(Record(fields={}), c, "SOFT")
        self.assertTrue(any("no entry" in f.detail for f in out))

if __name__ == "__main__":
    unittest.main()
