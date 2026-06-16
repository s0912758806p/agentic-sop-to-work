import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alcoaguard.arithmetic import recompute

class TestArithmetic(unittest.TestCase):
    def test_count_match(self):
        ok, derived, _ = recompute("count", [1, 2, 3], 3)
        self.assertTrue(ok); self.assertEqual(derived, 3)

    def test_sum_mismatch(self):
        ok, derived, _ = recompute("sum", [1, 2, 3], 7)
        self.assertFalse(ok); self.assertEqual(derived, 6)

    def test_mean_isclose(self):
        ok, derived, _ = recompute("mean", [1, 2, 3], 2.0)
        self.assertTrue(ok); self.assertAlmostEqual(derived, 2.0)

    def test_non_numeric_item(self):
        ok, derived, reason = recompute("sum", [1, "x"], 1)
        self.assertFalse(ok); self.assertIn("non-numeric", reason)

    def test_unknown_op(self):
        ok, _, reason = recompute("median", [1, 2], 1.5)
        self.assertFalse(ok); self.assertIn("unknown op", reason)

if __name__ == "__main__":
    unittest.main()
