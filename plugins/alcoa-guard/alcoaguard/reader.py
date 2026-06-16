# SPDX-License-Identifier: MIT
"""Read a record into the normalized model. DEGRADED: CSV/JSON file. FULL: a kit run dir."""
import csv
import json
import os
from .model import Record, Entry


def read_degraded(record_path, contract):
    if record_path.endswith(".json"):
        with open(record_path, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            fields = raw.get("fields", {})
            entries = [Entry(**e) for e in raw.get("entries", [])]
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
    """Return (Record, run_data). Reads the last JSON artifact named in run_manifest.json."""
    with open(os.path.join(run_dir, "run_manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    json_arts = [s.get("out") for s in manifest.get("steps", [])
                 if str(s.get("out", "")).endswith(".json")]
    run_data, fields = {}, {}
    data_path = json_arts[-1] if json_arts else None
    if data_path and os.path.exists(data_path):
        with open(data_path, encoding="utf-8") as f:
            run_data = json.load(f)
        for k, v in (run_data.get("data", {}) or {}).items():
            fields[k] = v
    return Record(fields=fields, entries=[], mode="FULL", source=run_dir), run_data
