# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic bounded-state policy for the kit's run-state (Loop Engineering cut #3).

Pure functions over passed-in data — NO file I/O, NO LLM. Callers own all reads/writes/deletes:
  verify.py rotates regression_log.jsonl to log_keep_count() lines (auto, low-risk).
  run.py --prune evicts the run dirs returned by runs_to_evict() (explicit, human-authorized).

log_floor deterministically protects cut #2's health windows from an aggressive keep_log.
"""


def log_keep_count(keep_log=200, log_floor=50):
    """Regression-log lines to keep. Never below log_floor (protects cut #2 health windows)."""
    return max(keep_log, log_floor)


def runs_to_evict(run_entries, keep_runs=20):
    """run_entries: list of (run_id, mtime). Keep the newest keep_runs (by mtime, then run_id);
    return the run_ids to evict. <= keep_runs entries → []. Deterministic via the run_id tiebreak.
    Negative keep_runs is clamped to 0."""
    if keep_runs < 0:
        keep_runs = 0
    ordered = sorted(run_entries, key=lambda e: (e[1], e[0]), reverse=True)
    return [rid for rid, _ in ordered[keep_runs:]]
