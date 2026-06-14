# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""DEGRADED-mode best-effort extraction.

No kit trace exists, so we tokenize user-supplied inputs into a best-effort allow-set
and scan the plain document for numeric / identifier / 【待補】 claims. This is lossy by
design — findings built on it are SOFT (see checks._sev) — and #1 (verdicts/aggregates)
is largely left to the advisory LLM layer, which is better at parsing prose.
"""
import os
import re

from . import core
from .model import Claim

_PLACEHOLDER = "【待補】"
_LEAD_NUM = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
_STRIP = " \t\r\n:;,.()[]%<>="  # surrounding punctuation peeled off a token


def _clean(tok):
    return tok.strip(_STRIP)


def _has_letter_and_digit(s):
    return any(c.isalpha() for c in s) and any(c.isdigit() for c in s)


def _classify(token):
    """(kind, value) for a token, or (None, None). kind in number|identifier|placeholder."""
    if _PLACEHOLDER in token:
        return "placeholder", _PLACEHOLDER
    t = _clean(token)
    if not t:
        return None, None
    if _has_letter_and_digit(t):
        return "identifier", t  # lot / batch / date-code / condition
    m = _LEAD_NUM.match(t)
    if m and m.group(0) == t:    # whole token is numeric (avoids grabbing a year out of a date)
        num = core.to_number(t)
        if num is not None:
            return "number", num
    return None, None


def _fmt_num(num):
    if isinstance(num, float) and num.is_integer():
        return str(int(num))
    return str(num)


def extract_sources_from_text(text, source_name):
    srcs = []
    for ln, line in enumerate(text.splitlines(), start=1):
        for tok in line.split():
            kind, val = _classify(tok)
            if kind in (None, "placeholder"):
                continue
            value = val if kind == "identifier" else _fmt_num(val)
            srcs.append({"value": value, "source": source_name, "locator": f"line {ln}"})
    return srcs


def extract_sources(paths):
    out = []
    for p in paths or []:
        try:
            with open(p, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        out.extend(extract_sources_from_text(text, os.path.basename(p)))
    return out


def _label_for(line, token):
    pos = line.find(token)
    if pos <= 0:
        return None
    pre = line[:pos].strip().rstrip(":").strip()
    return pre[-30:] or None


def extract_claims(doc_text, sources):
    claims, idx = [], 0
    for ln, line in enumerate(doc_text.splitlines(), start=1):
        for tok in line.split():
            kind, val = _classify(tok)
            if kind is None:
                continue
            idx += 1
            label = _label_for(line, tok)
            loc = f"doc:line {ln}"
            if kind == "placeholder":
                claims.append(Claim(id=f"doc#{idx}", value=_PLACEHOLDER, label=label,
                                    location=loc, kind="placeholder", sourced=None))
            else:
                claims.append(Claim(id=f"doc#{idx}", value=val, label=label,
                                    location=loc, kind=kind,
                                    sourced=core.is_sourced(val, sources)))
    return claims
