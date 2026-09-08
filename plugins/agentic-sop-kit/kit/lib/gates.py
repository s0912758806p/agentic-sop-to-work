# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic, hermetic gates for the flow engine.

Each gate is a pure function gate(artifact: dict, args: dict) -> (ok: bool, reason: str).
Gates only READ the artifact — no side effects, no network, no LLM. Run AFTER a step
writes its output artifact; a False result stops the run like a failed step.
"""
import math

import schema  # noqa: E402  (lib/ is on sys.path — callers insert it before importing)


def _get(data, path):
    """Dotted-path lookup. Returns (found: bool, value)."""
    cur = data
    for part in (path or "").split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def cmd_gate(artifact, args):
    data = artifact.get("data", {})
    code = data.get("exit")
    if code != 0:
        return False, f"cmd exited {code}: {(data.get('stderr') or '')[:300]}"
    must = args.get("stdout_contains")
    if must and must not in (data.get("stdout") or ""):
        return False, f"stdout missing expected text: {must!r}"
    return True, "ok"


def schema_gate(artifact, args):
    """Required-field check, plus (when the edge declares `schema_ref`) a typed-edge check.

    Backward compatible by construction: with no `schema_ref` this is exactly the
    pre-graph behaviour — `required` only, and `{}` passes anything. Adopted flows that
    never declare a ref (e.g. the shipped be.json) see no change.
    """
    data = artifact.get("data", {})
    missing = [k for k in args.get("required", []) if k not in data]
    if missing:
        return False, f"missing required fields: {missing}"
    ref = args.get("schema_ref")
    if ref:
        registry = schema.load_registry(args.get("schema_dir"))
        return schema.validate(artifact, registry, expected=ref)
    return True, "ok"


def trace_gate(artifact, args):
    """Every value under args['fields'] must appear verbatim among the artifact's trace sources.

    Comparison is by str(value): store trace values as the string form you expect
    (e.g. "12.0" for a float 12.0).
    """
    found, values = _get(artifact.get("data", {}), args.get("fields"))
    if not found:
        return False, f"trace_gate: path not found: {args.get('fields')!r}"
    sourced = {str(t.get("value")) for t in artifact.get("trace", [])}
    vals = values if isinstance(values, list) else [values]
    unsourced = [str(v) for v in vals if str(v) not in sourced]
    if unsourced:
        return False, f"values not traceable to input (possible fabrication): {unsourced}"
    return True, "ok"


def recompute_gate(artifact, args):
    """Re-derive an aggregate over a list path and compare to a stated value path.

    op="count" uses exact integer equality; op="sum" uses a tolerant float compare
    (math.isclose) to avoid float-representation false negatives. Never raises: a
    non-numeric stated value returns (False, reason), preserving the gate contract.
    """
    data = artifact.get("data", {})
    ok_over, items = _get(data, args.get("over"))
    ok_eq, claimed = _get(data, args.get("equals"))
    if not (ok_over and ok_eq):
        return False, f"recompute_gate: path missing (over={args.get('over')!r}, equals={args.get('equals')!r})"
    if not isinstance(items, list):
        return False, "recompute_gate: 'over' is not a list"
    op = args.get("op")
    if op == "count":
        actual = len(items)
    elif op == "sum":
        try:
            actual = sum(float(x) for x in items)
        except (TypeError, ValueError) as e:
            return False, f"recompute_gate: sum failed: {e}"
    else:
        return False, f"recompute_gate: unknown op {op!r}"
    try:
        claimed_num = float(claimed)
    except (TypeError, ValueError):
        return False, f"recompute_gate: stated value not numeric: {claimed!r}"
    if op == "count":
        matched = actual == claimed_num
    else:
        matched = math.isclose(actual, claimed_num, rel_tol=1e-9, abs_tol=1e-12)
    if not matched:
        return False, f"recompute mismatch: computed {actual} vs stated {claimed}"
    return True, "ok"


PLACEHOLDER = "【待補】"


def _count_marker(value, marker):
    """Occurrences of `marker` anywhere in a nested data value."""
    if isinstance(value, str):
        return 1 if marker in value else 0
    if isinstance(value, dict):
        return sum(_count_marker(v, marker) for v in value.values())
    if isinstance(value, list):
        return sum(_count_marker(v, marker) for v in value)
    return 0


def residual_gate(artifact, args):
    """Residual-placeholder scan on the artifact's own output.

    The kit's first rule is 缺值標【待補】、絕不臆造, yet nothing here used to check the kit's
    own output for leftovers (alcoa-guard checks required fields of a different input;
    second-opinion deliberately lets the placeholder pass as an honest blank).

    The split matches the house hard/advisory doctrine:
      • a path declared in args['required'] that is missing or still holds the marker → FAIL
        (that is unfinished work, not an honest blank)
      • the marker anywhere else → legitimate and preserved, and never blocking
    """
    marker = args.get("marker", PLACEHOLDER)
    data = artifact.get("data", {})
    unfilled = []
    for path in args.get("required", []):
        found, value = _get(data, path)
        if not found:
            unfilled.append(f"{path} (absent)")
        elif _count_marker(value, marker):
            unfilled.append(path)
    if unfilled:
        return False, (f"required fields still unfilled ｜ 必填欄位仍是{marker}: {unfilled} — "
                       f"fill them or remove the field; never invent a value")
    return True, "ok"


REGISTRY = {"cmd_gate": cmd_gate, "schema_gate": schema_gate,
            "trace_gate": trace_gate, "recompute_gate": recompute_gate,
            "residual_gate": residual_gate}


def run_gate(gate_type, artifact, args=None):
    fn = REGISTRY.get(gate_type)
    if fn is None:
        return False, f"unknown gate type: {gate_type!r}"
    return fn(artifact, args or {})
