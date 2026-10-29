# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The honest-blank marker, defined once.

`【待補】` ("to be filled") is what a DRAFT writes where it has no sourced value, instead of
inventing one. Its MEANING differs per plugin on purpose — a domain decision, not drift:
  • second-opinion-honesty SKIPS it: an honest blank is not a fabrication, so a 【待補】
    slot never becomes a #2/#3 finding.
  • alcoa-guard FLAGS it: a required field that still holds 【待補】 is not Complete (the C
    in ALCOA+), so it is a finding.
Both read the same constant; only the policy on top differs.
"""

TBD = "【待補】"


def is_tbd(value):
    """True iff the value IS the placeholder (surrounding whitespace ignored)."""
    return value is not None and str(value).strip() == TBD


def contains_tbd(value):
    """True iff the placeholder appears anywhere in the value."""
    return value is not None and TBD in str(value)
