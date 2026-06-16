# SPDX-License-Identifier: MIT
"""Run the five ALCOA+ rule clusters over a record, dedupe, and assemble a Verdict.
FULL mode findings are HARD; DEGRADED findings are SOFT. A deterministic GREEN always still
ships the human-judgment checklist so it cannot be read as 'fully compliant'."""
from datetime import date
from .model import Verdict
from .rules import attributable, temporal, complete, accurate, consistent

RULES = [
    ("attributable", attributable),
    ("contemporaneous", temporal),
    ("complete", complete),
    ("accurate", accurate),
    ("consistent", consistent),
]

HUMAN_CHECKLIST = [
    "Attributable: confirm the named operator was authorized for this task.",
    "Contemporaneous: confirm any gap between performance and recording is justified.",
    "Original: confirm records are originals or certified true copies.",
    "Accurate: confirm source measurements reflect reality, not just internal consistency.",
]


def run_rules(record, contract, as_of=None, only=None):
    severity = "HARD" if record.mode == "FULL" else "SOFT"
    if as_of is None:
        as_of = date.today()
    findings = []
    for name, mod in RULES:
        if only and name not in only:
            continue
        if mod is temporal:
            findings.extend(mod.check(record, contract, severity, as_of=as_of))
        else:
            findings.extend(mod.check(record, contract, severity))
    seen, deduped = set(), []
    for f in findings:
        if f.id not in seen:
            seen.add(f.id)
            deduped.append(f)
    hard = sum(1 for f in deduped if f.severity == "HARD")
    soft = sum(1 for f in deduped if f.severity == "SOFT")
    return Verdict(mode=record.mode, hard=hard, soft=soft,
                   human_items=len(HUMAN_CHECKLIST), findings=deduped,
                   checklist=list(HUMAN_CHECKLIST))
