# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The human acknowledgement that unblocks the 做法 3 gate.

A human runs `python3 -m secondop.ack` after reviewing a Second Opinion report. You can
only acknowledge a run that HAS a review (review first, then ack); the `.ack` record
captures who/when/note so the decision is on the audit trail. This is deliberately the
HUMAN's action — the gate enforces that an ack exists, preserving "human owns the verdict".
"""
import argparse
import json
import os
import sys
from datetime import datetime

from . import gate


class AckError(Exception):
    """Acknowledgement preconditions not met (no run, or no review to acknowledge)."""


def ack(project, run_id=None, note=None, user=None):
    if run_id is None:
        run_id = gate.latest_run_id(project)
    if not run_id:
        raise AckError("no DRAFT run found to acknowledge")
    rd = gate.review_dir(project, run_id)
    if not gate.review_exists(project, run_id):
        raise AckError(f"no Second Opinion review for {run_id}; run /second-opinion first")
    os.makedirs(rd, exist_ok=True)
    rec = {
        "acknowledged": True,
        "run_id": run_id,
        "by": user or os.environ.get("USER") or "unknown",
        "at": datetime.now().isoformat(timespec="seconds"),
        "note": note or "",
    }
    path = os.path.join(rd, ".ack")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return path, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="Acknowledge a Second Opinion review (human action).")
    ap.add_argument("--project", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--run-id", default=None, help="default: the latest DRAFT run")
    ap.add_argument("--note", default=None)
    ap.add_argument("--by", default=None, help="who is acknowledging (default $USER)")
    a = ap.parse_args(argv)
    try:
        path, rec = ack(a.project, run_id=a.run_id, note=a.note, user=a.by)
    except AckError as e:
        print(f"[second-opinion] {e}", file=sys.stderr)
        return 2
    print(f"[second-opinion] acknowledged {rec['run_id']} by {rec['by']} → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
