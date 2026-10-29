# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Severity, a minimal Finding base, and the dedupe + HARD/SOFT count every companion needs.

The helpers are duck-typed: they work on any object with `.id` and `.severity`, so each
plugin keeps its own Finding dataclass (and its published report fields) while sharing the
counting rule. `Finding` here is the base for new plugins (plugin-forge scaffolds use it).
"""
from dataclasses import dataclass


class Severity:
    HARD = "HARD"   # deterministic + authoritative evidence; a gate may act on it
    SOFT = "SOFT"   # reconstructed evidence or advisory; never gates


@dataclass
class Finding:
    id: str
    severity: str
    location: str = ""
    detail: str = ""


def dedupe(findings, key=None):
    """Drop findings whose key was already seen. First occurrence wins; order is kept."""
    key = key or (lambda f: f.id)
    seen, out = set(), []
    for f in findings:
        k = key(f)
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def count(findings):
    """(hard, soft) counts."""
    hard = sum(1 for f in findings if f.severity == Severity.HARD)
    soft = sum(1 for f in findings if f.severity == Severity.SOFT)
    return hard, soft
