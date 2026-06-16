# SPDX-License-Identifier: MIT
"""A — Attributable: every entry that needs attribution has a non-empty author + timestamp."""
from ..model import Finding


def check(record, contract, severity):
    findings = []
    need = list(contract.attribution)
    seen = {f: False for f in need}
    for e in record.entries:
        if e.field in seen:
            seen[e.field] = True
            if not (e.author and str(e.author).strip()):
                findings.append(Finding(
                    id=f"attributable:author:{e.field}", principle="attributable",
                    severity=severity, origin="deterministic", location=e.field,
                    detail="entry requires an author but none was recorded"))
            if not (e.timestamp and str(e.timestamp).strip()):
                findings.append(Finding(
                    id=f"attributable:ts:{e.field}", principle="attributable",
                    severity=severity, origin="deterministic", location=e.field,
                    detail="entry requires a timestamp but none was recorded"))
    for f, ok in seen.items():
        if not ok:
            findings.append(Finding(
                id=f"attributable:missing:{f}", principle="attributable",
                severity=severity, origin="deterministic", location=f,
                detail="field requires attribution but no entry present"))
    return findings
