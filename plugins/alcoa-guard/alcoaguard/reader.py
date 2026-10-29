# SPDX-License-Identifier: MIT
"""Read a record into the normalized model. DEGRADED: CSV/JSON file. FULL: a kit run dir,
read through _core/run_contract.py — the suite's single definition of a run dir (only an
OK_FOR_REVIEW run is read; a FAILED one raises RunNotReviewable; `branch→` entries are
skipped; a relocated run resolves by basename)."""
import csv
import json
from dataclasses import fields as dc_fields
from ._core import run_contract
from ._core.run_contract import ContractError, NotAKitRun, RunNotReviewable  # noqa: F401
from .model import Record, Entry


def read_degraded(record_path, contract):
    if record_path.endswith(".json"):
        with open(record_path, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            fields = raw.get("fields", {})
            _ef = {f.name for f in dc_fields(Entry)}
            entries = [Entry(**{k: v for k, v in e.items() if k in _ef})
                       for e in raw.get("entries", []) if isinstance(e, dict)]
        else:
            fields, entries = {}, []
        return Record(fields=fields, entries=entries, mode="DEGRADED", source=record_path)
    entries, fields = [], {}
    with open(record_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            e = Entry(field=row.get("field", ""), value=row.get("value", ""),
                      author=(row.get("author") or None),
                      timestamp=(row.get("timestamp") or None),
                      kind=row.get("kind", "text"))
            entries.append(e)
            fields[e.field] = e.value
    return Record(fields=fields, entries=entries, mode="DEGRADED", source=record_path)


def read_full(run_dir):
    """Return (Record, run_data): run_data is the artifact that feeds the run's deliverable
    (final_output when JSON, else the last JSON step artifact). Raises
    run_contract.ContractError (NotAKitRun / RunNotReviewable) for a non-reviewable run."""
    rc = run_contract.load(run_dir)
    art = rc.feeding_artifact()
    run_data, fields = {}, {}
    if art is not None:
        run_data = {"schema": art.schema, "produced_by": art.produced_by,
                    "data": art.data, "trace": art.trace}
        data = art.data if isinstance(art.data, dict) else {}
        fields.update(data)
    return Record(fields=fields, entries=[], mode="FULL", source=run_dir,
                  run_id=rc.run_id), run_data
