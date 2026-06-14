# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""做法 3 — the opt-in enforced ack gate (decision side).

`decide()` is a pure function so the policy is trivially testable; hooks/stop_ack.py is a
thin IO wrapper. The gate enforces THAT a human acknowledged a Second Opinion review of
the latest DRAFT run — never WHAT they decided — and is anti-loop capped (mirrors the kit
Stop-hook: stop_hook_active + a retry counter capped by SECONDOP_MAX_ACK_RETRIES).
"""
import os

DEFAULT_MAX_ACK_RETRIES = 3
_ENV = "SECONDOP_MAX_ACK_RETRIES"


def max_ack_retries():
    try:
        v = int(os.environ.get(_ENV, str(DEFAULT_MAX_ACK_RETRIES)))
    except ValueError:
        v = DEFAULT_MAX_ACK_RETRIES
    return max(0, v)


def require_ack_enabled(project):
    """Opt-in marker: the project chose to enforce the gate."""
    return os.path.exists(os.path.join(project, ".second-opinion", "require_ack"))


def latest_run_id(project):
    """Newest DRAFT run under the kit's .agentic-sop-runs/ (run ids sort chronologically)."""
    base = os.path.join(project, ".agentic-sop-runs")
    if not os.path.isdir(base):
        return None
    runs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    return runs[-1] if runs else None


def review_dir(project, run_id):
    return os.path.join(project, ".second-opinion-runs", run_id)


def review_exists(project, run_id):
    return os.path.exists(os.path.join(review_dir(project, run_id), "second_opinion.json"))


def is_acked(project, run_id):
    return os.path.exists(os.path.join(review_dir(project, run_id), ".ack"))


def decide(require_ack, latest_run_id, review_exists, acked, stop_active, retry_count, max_retries):
    """Pure policy. Returns (block: bool, reason: str, next_count: int)."""
    if not require_ack:
        return (False, "ack gate not enabled (opt-in)", 0)
    if not latest_run_id:
        return (False, "no DRAFT run to review", 0)
    if review_exists and acked:
        return (False, f"run {latest_run_id} reviewed and acknowledged", 0)
    if stop_active and retry_count >= max_retries:
        return (False, f"ack gate: retry cap ({max_retries}) reached — handing to human", retry_count)
    missing = "has no Second Opinion review" if not review_exists else "review is not acknowledged by a human"
    reason = (f"DRAFT run {latest_run_id} {missing}. Run `/second-opinion <run_dir>` then "
              f"`python3 -m secondop.ack` (a human action) before stopping.")
    return (True, reason, retry_count + 1)
