# SPDX-License-Identifier: MIT
"""C — Contemporaneous: no future dates; declared date_order relations hold (catches backdating)."""
from datetime import datetime
from ..model import Finding

_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d")


def _parse(s):
    if s is None:
        return None
    s = str(s).strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def check(record, contract, severity, as_of=None):
    findings, vals = [], {}
    for f in contract.date_fields:
        raw = record.fields.get(f)
        dt = _parse(raw)
        if raw is not None and dt is None:
            findings.append(Finding(
                id=f"contemporaneous:baddate:{f}", principle="contemporaneous",
                severity=severity, origin="deterministic", location=f,
                detail=f"unparseable date: {raw!r}"))
        elif dt is not None:
            vals[f] = dt
    if contract.no_future and as_of is not None:
        for f, dt in vals.items():
            if dt.date() > as_of:
                findings.append(Finding(
                    id=f"contemporaneous:future:{f}", principle="contemporaneous",
                    severity=severity, origin="deterministic", location=f,
                    detail=f"date {dt.date()} is in the future (as_of {as_of})"))
    for pair in contract.date_order:
        earlier, later = pair[0], pair[1]
        de, dl = vals.get(earlier), vals.get(later)
        if de and dl and de > dl:
            findings.append(Finding(
                id=f"contemporaneous:order:{earlier}>{later}", principle="contemporaneous",
                severity=severity, origin="deterministic", location=f"{earlier},{later}",
                detail=f"{earlier} ({de.date()}) is after {later} ({dl.date()}) — ordering/backdating violation"))
    return findings
