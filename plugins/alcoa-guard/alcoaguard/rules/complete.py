# SPDX-License-Identifier: MIT
"""C — Complete: required fields present + non-blank + not 【待補】; expected sets fully present."""
from ..model import Finding

PLACEHOLDER = "【待補】"


def check(record, contract, severity):
    findings = []
    for f in contract.required_fields:
        v = record.fields.get(f)
        if v is None or str(v).strip() == "" or PLACEHOLDER in str(v):
            findings.append(Finding(
                id=f"complete:required:{f}", principle="complete", severity=severity,
                origin="deterministic", location=f,
                detail="required field is missing / blank / 【待補】"))
    for f, members in contract.expected_set.items():
        present = record.fields.get(f)
        present_keys = set()
        if isinstance(present, list):
            for item in present:
                present_keys.add(item.get("id") if isinstance(item, dict) else item)
        for m in members:
            if m not in present_keys:
                findings.append(Finding(
                    id=f"complete:set:{f}:{m}", principle="complete", severity=severity,
                    origin="deterministic", location=f,
                    detail=f"expected member {m!r} missing from {f!r}"))
    return findings
