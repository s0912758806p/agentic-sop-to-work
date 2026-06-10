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


REGISTRY = {"cmd_gate": cmd_gate, "schema_gate": schema_gate}


def run_gate(gate_type, artifact, args=None):
    fn = REGISTRY.get(gate_type)
    if fn is None:
        return False, f"unknown gate type: {gate_type!r}"
    return fn(artifact, args or {})
