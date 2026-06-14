# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Matching kernels + stdlib JSON/path helpers.

These re-implement (never import) the slice of the agentic-sop-kit contract that
Second Opinion needs to READ. The load-bearing detail: the kit stores a float `250.0`
in `data` but the string `"250"` in `trace`, so provenance matching must be NUMERIC
(isclose), not a raw `str(v) in sources` (which would false-positive on float format).
"""
import json
import math
import os

_TOL = dict(rel_tol=1e-9, abs_tol=1e-12)  # mirror the kit recompute_gate tolerances


def to_number(x):
    """float(x) for ints/floats and clean numeric strings; else None.

    Strict on purpose: '0.7%' and 'B-2407-X' → None. Stripping units/identifiers is
    extract.py's job, not this kernel's.
    """
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def is_sourced(value, sources):
    """True iff `value` is backed by some trace/source token.

    Numeric values match numerically (isclose) so data `250.0` == trace `"250"`.
    Non-numeric values match by case-insensitive, trimmed string equality.
    `sources` is a list of dicts each carrying a "value" (the kit trace shape).
    """
    num = to_number(value)
    if num is not None:
        for s in sources:
            tnum = to_number(s.get("value"))
            if tnum is not None and math.isclose(num, tnum, **_TOL):
                return True
        return False
    norm = str(value).strip().casefold()
    if not norm:
        return True  # nothing to fabricate
    for s in sources:
        if str(s.get("value")).strip().casefold() == norm:
            return True
    return False


def nearest_token(value, sources):
    """Closest NUMERIC source token to a numeric `value` (transcription-error hint).

    Returns the source dict, or None when `value` isn't numeric or no numeric sources.
    """
    num = to_number(value)
    if num is None:
        return None
    best, best_d = None, None
    for s in sources:
        tnum = to_number(s.get("value"))
        if tnum is None:
            continue
        d = abs(num - tnum)
        if best_d is None or d < best_d:
            best, best_d = s, d
    return best


# --- stdlib JSON / path helpers (re-implemented; NOT imported from the kit) ---
def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path
