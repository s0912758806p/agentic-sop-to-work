# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic control-flow helpers for the workflow engine (no LLM, no side effects).

Branching is decided by code: a predicate over a prior step's artifact data, or a router
skill's output read as a normal data field. The model never decides the next step.
"""

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "in": lambda a, b: a in b,
}


def _path(data, dotted):
    cur = data
    for part in (dotted or "").split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def eval_predicate(when, data):
    """Evaluate {path, op, value} (op 'exists' needs no value) against data. Deterministic; never raises."""
    op = when.get("op")
    found, actual = _path(data, when.get("path"))
    if op == "exists":
        return found
    if not found:
        return False
    fn = _OPS.get(op)
    if fn is None:
        return False
    try:
        return bool(fn(actual, when.get("value")))
    except TypeError:
        return False


def resolve_branch(cases, data):
    """First case whose `when` matches wins; otherwise the `default` case (placement-independent).

    A `when` match always takes precedence over `default`, regardless of where `default` is listed.
    Returns (goto, reason); (None, reason) if neither a `when` nor a `default` matches.
    """
    default_case = None
    for case in cases:
        if "when" in case and eval_predicate(case["when"], data):
            return case.get("goto"), "matched"
        if case.get("default") and default_case is None:
            default_case = case
    if default_case is not None:
        return default_case.get("goto"), "default"
    return None, "no case matched and no default"
