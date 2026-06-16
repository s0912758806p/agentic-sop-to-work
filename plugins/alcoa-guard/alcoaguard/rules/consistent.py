# SPDX-License-Identifier: MIT
"""C — Consistent: ID fields match their declared pattern; values carry their expected unit."""
import re
from ..model import Finding


def check(record, contract, severity):
    findings = []
    for f, pat in contract.id_patterns.items():
        v = record.fields.get(f)
        if v is None:
            continue
        try:
            matched = re.fullmatch(pat, str(v))
        except re.error as exc:
            findings.append(Finding(
                id=f"consistent:id:{f}", principle="consistent", severity=severity,
                origin="deterministic", location=f,
                detail=f"invalid id_pattern for {f!r}: {exc}"))
            continue
        if not matched:
            findings.append(Finding(
                id=f"consistent:id:{f}", principle="consistent", severity=severity,
                origin="deterministic", location=f,
                detail=f"value {v!r} does not match required pattern {pat!r}"))
    for f, unit in contract.units.items():
        v = record.fields.get(f)
        if v is not None and not re.search(
                r"(?<![A-Za-z])" + re.escape(unit) + r"(?![A-Za-z])", str(v)):
            findings.append(Finding(
                id=f"consistent:unit:{f}", principle="consistent", severity=severity,
                origin="deterministic", location=f,
                detail=f"value {v!r} missing expected unit {unit!r}"))
    return findings
