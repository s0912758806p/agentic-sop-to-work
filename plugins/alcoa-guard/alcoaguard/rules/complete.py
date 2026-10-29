# SPDX-License-Identifier: MIT
"""C — Complete: required fields present + non-blank + not 【待補】; expected sets fully present."""
from .._core.markers import TBD as PLACEHOLDER, contains_tbd
from ..model import Finding

# 【待補】 in a required field is a Complete VIOLATION here — the opposite of second-opinion,
# which skips it as an honest blank. Deliberate; see _core/markers.py.


def check(record, contract, severity):
    findings = []
    for f in contract.required_fields:
        v = record.fields.get(f)
        if v is None or str(v).strip() == "" or contains_tbd(v):
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
