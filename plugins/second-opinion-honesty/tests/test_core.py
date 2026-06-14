# SPDX-License-Identifier: MIT
"""RED-first tests for secondop.core matching kernels.

The kit stores a float `250.0` in `data` but the string `"250"` in `trace`. A raw
`str(v) in sources` (what trace_gate does) would FALSE-POSITIVE here. is_sourced must
match NUMERICALLY (isclose), so these tests pin that behavior.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # plugin root
from secondop import core  # noqa: E402

SOURCES = [{"value": "99.4"}, {"value": "0.3"}, {"value": "7.1"},
           {"value": "250"}, {"value": "0.12"}]


class TestToNumber(unittest.TestCase):
    def test_integer_like_string(self):
        self.assertEqual(core.to_number("250"), 250.0)

    def test_float_string(self):
        self.assertEqual(core.to_number("99.4"), 99.4)

    def test_thousands_separator(self):
        self.assertEqual(core.to_number("1,234"), 1234.0)

    def test_passthrough_actual_number(self):
        self.assertEqual(core.to_number(250.0), 250.0)

    def test_alpha_identifier_is_none(self):
        self.assertIsNone(core.to_number("B-2407-X"))

    def test_unit_suffix_is_none(self):
        # to_number is strict; stripping units is extract.py's job
        self.assertIsNone(core.to_number("0.7%"))


class TestIsSourced(unittest.TestCase):
    def test_float_data_matches_integer_trace_token(self):
        # data 250.0 vs trace "250" must NOT read as fabrication
        self.assertTrue(core.is_sourced(250.0, SOURCES))

    def test_exact_float_match(self):
        self.assertTrue(core.is_sourced(99.4, SOURCES))

    def test_fabricated_number_not_sourced(self):
        self.assertFalse(core.is_sourced(0.7, SOURCES))

    def test_string_identifier_not_sourced(self):
        self.assertFalse(core.is_sourced("B-2407-X", SOURCES))

    def test_string_match_is_case_insensitive(self):
        self.assertTrue(core.is_sourced("Acetaminophen", [{"value": "acetaminophen"}]))


class TestNearestToken(unittest.TestCase):
    def test_nearest_numeric_token(self):
        n = core.nearest_token(0.7, SOURCES)
        self.assertIsNotNone(n)
        self.assertEqual(n["value"], "0.3")

    def test_nearest_none_when_no_numeric_sources(self):
        self.assertIsNone(core.nearest_token(0.7, [{"value": "abc"}]))


if __name__ == "__main__":
    unittest.main()
