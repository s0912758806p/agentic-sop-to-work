# SPDX-License-Identifier: MIT
"""Load an explicit integrity contract, or infer a best-effort one from a kit run.
Inference is deliberately conservative: it only sets what a domain-neutral convention makes
unambiguous; everything else is left empty so it becomes a human-judgment checklist item
(鐵則: uncertain -> human, never invent a violation)."""
import json
from .model import IntegrityContract


def from_dict(d):
    return IntegrityContract(
        required_fields=list(d.get("required_fields", [])),
        date_fields=list(d.get("date_fields", [])),
        date_order=[list(p) for p in d.get("date_order", [])],
        no_future=bool(d.get("no_future", False)),
        attribution=list(d.get("attribution", [])),
        id_patterns=dict(d.get("id_patterns", {})),
        units=dict(d.get("units", {})),
        limits=dict(d.get("limits", {})),
        aggregates=list(d.get("aggregates", [])),
        expected_set=dict(d.get("expected_set", {})),
    )


def load(path):
    with open(path, encoding="utf-8") as f:
        return from_dict(json.load(f))


def infer_from_run(run_data):
    c = IntegrityContract()
    data = run_data.get("data", {}) if isinstance(run_data, dict) else {}
    results = data.get("results")
    if isinstance(results, list):
        ids = [r.get("id") for r in results if isinstance(r, dict) and r.get("id")]
        if ids:
            c.expected_set["results"] = ids
    aggs = data.get("aggregates")
    if isinstance(aggs, list):
        c.aggregates = [{"op": a.get("op"), "over": a.get("over"), "stated": a.get("stated")}
                        for a in aggs
                        if isinstance(a, dict) and a.get("op") and a.get("over")
                        and a.get("stated") is not None]
    return c
