import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.model import Record, IntegrityContract
from alcoaguard.rules import complete

class TestComplete(unittest.TestCase):
    def test_required_present(self):
        r = Record(fields={"a": "x"})
        c = IntegrityContract(required_fields=["a"])
        self.assertEqual(complete.check(r, c, "HARD"), [])

    def test_blank_and_placeholder(self):
        r = Record(fields={"a": "", "b": "【待補】"})
        c = IntegrityContract(required_fields=["a", "b"])
        out = complete.check(r, c, "HARD")
        self.assertEqual(len(out), 2)

    def test_expected_set_missing_member(self):
        r = Record(fields={"timepoints": ["0M", "3M"]})
        c = IntegrityContract(expected_set={"timepoints": ["0M", "3M", "6M"]})
        out = complete.check(r, c, "HARD")
        self.assertTrue(any("6M" in f.detail for f in out))

if __name__ == "__main__":
    unittest.main()
