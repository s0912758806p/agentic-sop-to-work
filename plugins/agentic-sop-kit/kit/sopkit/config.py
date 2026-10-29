# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The single reader of every SOPKIT_* environment variable.

Each value is read at CALL time, never at import time: before v1.11.0 `SOPKIT_ROOT` and
`SOPKIT_SCHEMA_DIR` were frozen when lib/kit.py / lib/schema.py were first imported, so
setting them later in the same process silently did nothing.

Pure stdlib, imports nothing from the kit — the hooks use it too, and a hook must keep
working even when the rest of the engine is broken.

    SOPKIT_ROOT                    kit root (default: the directory holding sopkit/)
    SOPKIT_SCHEMA_DIR              typed-edge declarations (default: <root>/workflow/schemas)
    SOPKIT_MAX_FIX_RETRIES         fix-loop / Stop-hook retry ceiling (3)
    SOPKIT_STALL_WINDOW            identical failures that count as a stall (2; 0 disables)
    SOPKIT_STATE_KEEP_RUNS         run dirs kept by run.py --prune (20)
    SOPKIT_STATE_KEEP_LOG          regression_log.jsonl lines kept (200; floor 50 in loop.state)
    SOPKIT_HEALTH_SLOWDOWN_FACTOR  slowdown advisory threshold (2.0)
    SOPKIT_HEALTH_FLAKY_WINDOW     recent runs inspected for flakiness (10)
"""
import os

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(name, default, cast):
    raw = os.environ.get(name)
    return cast(raw) if raw not in (None, "") else default


def kit_root():
    return os.environ.get("SOPKIT_ROOT") or _PKG_ROOT


def schema_dir():
    return os.environ.get("SOPKIT_SCHEMA_DIR") or os.path.join(kit_root(), "workflow", "schemas")


def max_fix_retries():
    return _env("SOPKIT_MAX_FIX_RETRIES", 3, int)


def stall_window():
    return _env("SOPKIT_STALL_WINDOW", 2, int)


def keep_runs():
    return _env("SOPKIT_STATE_KEEP_RUNS", 20, int)


def keep_log():
    return _env("SOPKIT_STATE_KEEP_LOG", 200, int)


def health_slowdown_factor():
    return _env("SOPKIT_HEALTH_SLOWDOWN_FACTOR", 2.0, float)


def health_flaky_window():
    return _env("SOPKIT_HEALTH_FLAKY_WINDOW", 10, int)
