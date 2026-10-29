# GENERATED from shared/sopcore/report.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: b251fcf6bde6f752edec73ea1da8959b3e6d648eaa2a00064512b4645bdeb948
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The DRAFT report frame and the md + json dual write.

An advisory report is built so it CANNOT express "approved": `verdict` is the frozen literal
ADVISORY_ONLY and `human_owns_verdict` is always True. Builders splat `frame()` into their
dict (so each plugin keeps its own schema tag, fields and key order), and `write_dual`
refuses to write an advisory report whose frame was tampered with.
"""
import json
import os

ADVISORY_ONLY = "ADVISORY_ONLY"


def frame():
    return {"verdict": ADVISORY_ONLY, "human_owns_verdict": True}


def check_frame(rep):
    if rep.get("verdict") != ADVISORY_ONLY or rep.get("human_owns_verdict") is not True:
        raise ValueError("advisory report must carry verdict=ADVISORY_ONLY and "
                         "human_owns_verdict=True — a DRAFT review never approves or rejects")


def write_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def write_dual(rep, out_dir, stem, to_markdown, advisory=True):
    """Write <out_dir>/<stem>.json and <stem>.md. Returns (json_path, md_path)."""
    if advisory:
        check_frame(rep)
    os.makedirs(out_dir, exist_ok=True)
    jpath = write_json(rep, os.path.join(out_dir, stem + ".json"))
    mpath = os.path.join(out_dir, stem + ".md")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(to_markdown(rep))
    return jpath, mpath
