# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Loop-control progress signal for the fix-loop (Loop Engineering cut #1: stall detection).

Deterministic, zero-LLM. Turns a single run.py failure into a reproducible 'progress
signature', and classifies a rolling signature history as idle / thrash / None.

Progress is measured ONLY from sensor output (the failure dict run.py already builds),
never from model self-report. 'artifact' is excluded (it carries the run id); the run dir
is stripped from the message so the same wall hashes the same across retries.

The comparison logic lives entirely in classify_progress() — the single point where a
future monotone 'variant' measure would slot in (northstar §5; not built in v1)."""
import hashlib
import re

_WS = re.compile(r"\s+")


def _normalize(failure, run_dir=None):
    """Run-agnostic projection of a failure. Uses only {step, gate_type, message};
    DROPS 'artifact' (it holds the $RUN path); replaces the literal run_dir in the
    message so per-run paths don't fake 'progress'."""
    step = str(failure.get("step", ""))
    gate_type = str(failure.get("gate_type") or "")
    message = str(failure.get("message", ""))
    if run_dir:
        message = message.replace(run_dir, "<RUN>")
    message = _WS.sub(" ", message).strip()
    return f"{step}|{gate_type}|{message}"


def progress_signature(failure, run_dir=None):
    """Stable 16-hex-char fingerprint of one failure. Same wall -> same signature."""
    return hashlib.sha256(_normalize(failure, run_dir).encode("utf-8")).hexdigest()[:16]


def classify_progress(history, window):
    """history: list[str] signatures, oldest->newest (current appended last).
    Returns 'idle' | 'thrash' | None.
      window <= 0 : stall disabled -> None.
      idle        : the last `window` signatures are all identical.
      thrash      : minimal A->B->A oscillation (cycle cap fixed at 2):
                    history[-1] == history[-3] and history[-1] != history[-2].
    Longer cycles / diverging novelty -> None (backstopped by the budget ceiling)."""
    if window <= 0:
        return None
    n = len(history)
    if n >= window and len(set(history[-window:])) == 1:
        return "idle"
    if n >= 3 and history[-1] == history[-3] and history[-1] != history[-2]:
        return "thrash"
    return None
