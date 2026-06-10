# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic, hermetic gates for the flow engine.

Each gate is a pure function gate(artifact: dict, args: dict) -> (ok: bool, reason: str).
Gates only READ the artifact — no side effects, no network, no LLM. Run AFTER a step
writes its output artifact; a False result stops the run like a failed step.
"""


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
    data = artifact.get("data", {})
    missing = [k for k in args.get("required", []) if k not in data]
    if missing:
        return False, f"missing required fields: {missing}"
    return True, "ok"


def trace_gate(artifact, args):
    """Every value under args['fields'] must appear verbatim among the artifact's trace sources."""
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
    """Re-derive an aggregate over a list path and compare to a stated value path."""
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
    if float(actual) != float(claimed):
        return False, f"recompute mismatch: computed {actual} vs stated {claimed}"
    return True, "ok"


REGISTRY = {"cmd_gate": cmd_gate, "schema_gate": schema_gate,
            "trace_gate": trace_gate, "recompute_gate": recompute_gate}


def run_gate(gate_type, artifact, args=None):
    fn = REGISTRY.get(gate_type)
    if fn is None:
        return False, f"unknown gate type: {gate_type!r}"
    return fn(artifact, args or {})
