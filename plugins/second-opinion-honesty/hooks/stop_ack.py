#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""做法 3 — opt-in, project-scoped Stop-hook (the IO wrapper around secondop.gate).

It blocks the session from stopping ONLY when the project opted in
(`.second-opinion/require_ack`) AND the latest DRAFT run lacks an acknowledged Second
Opinion review. It enforces THAT a human acknowledged a review — never WHAT they decided.
Anti-loop: mirrors the kit Stop-hook (stop_hook_active + a retry counter capped by
SECONDOP_MAX_ACK_RETRIES); at the cap it stops blocking and hands to the human. Always
exits 0 — blocking is signalled via the stdout JSON, never via the exit code. No-op (and
silent) in any project that did not opt in, so a global install never disturbs other work.
"""
import json
import os
import sys

ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from secondop import gate  # noqa: E402

PROJECT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
STATE_DIR = os.path.join(PROJECT, ".second-opinion")
COUNT = os.path.join(STATE_DIR, ".ack_retry_count")


def _stop_active():
    try:
        return bool(json.loads(sys.stdin.read() or "{}").get("stop_hook_active"))
    except (ValueError, OSError):
        return False


def _read_count():
    try:
        return int(open(COUNT, encoding="utf-8").read().strip() or "0")
    except (OSError, ValueError):
        return 0


def _write_count(n):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(COUNT, "w", encoding="utf-8") as f:
        f.write(str(n))


def main():
    if not gate.require_ack_enabled(PROJECT):
        return 0  # opt-in: silent no-op unless the project asked for the gate

    rid = gate.latest_run_id(PROJECT)
    review = gate.review_exists(PROJECT, rid) if rid else False
    acked = gate.is_acked(PROJECT, rid) if rid else False
    stop_active = _stop_active()
    count = _read_count() if stop_active else 0

    block, reason, nxt = gate.decide(
        True, rid, review, acked, stop_active, count, gate.max_ack_retries())

    if block:
        _write_count(nxt)
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    else:
        _write_count(0)  # satisfied, or handed to the human — reset the loop counter
    return 0


if __name__ == "__main__":
    sys.exit(main())
