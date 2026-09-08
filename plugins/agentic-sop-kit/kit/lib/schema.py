# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Typed handoff edges: give `artifact["schema"]` teeth.

Before this module the schema tag was decorative — `kit.artifact()` accepted any string
and no gate ever read it. In a linear pipeline that is technical debt; in a graph an
untyped edge means the handoff contract is fiction. A declaration here is the contract.

Deliberately NOT JSON Schema (rung 2/4: stdlib-only is machine-enforced by
tests/test_no_third_party.py and `plugin-forge lint --all --strict`). The vocabulary is
the minimum the engine needs — required field names plus scalar/container types. Nesting
and enums are declined until a real non-demo flow needs them (rung 6).

Declaration file (one per tag, under workflow/schemas/):

    {"schema": "readings@1",
     "required": ["readings", "skipped"],
     "types": {"readings": "list", "skipped": "list"}}

`required` and `types` are checked against the artifact's `data` object.
"""
import json
import os

import kit  # noqa: E402  (lib/ is on sys.path — callers insert it before importing)

DEFAULT_DIR = os.environ.get("SOPKIT_SCHEMA_DIR") or kit.kit_path("workflow", "schemas")

# An unknown type name is a declaration bug, not a licence to skip the check — see _check_type.
_TYPES = {
    "list": lambda v: isinstance(v, list),
    "dict": lambda v: isinstance(v, dict),
    "str": lambda v: isinstance(v, str),
    # bool is a subclass of int in Python; True must not pass as a number.
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "bool": lambda v: isinstance(v, bool),
}


def load_registry(schema_dir=None):
    """Read every *.json declaration in `schema_dir`, keyed by its declared `schema` tag
    (the tag inside the file wins — a filename can never disagree with the contract).
    A missing directory yields an empty registry rather than raising: an adopted project
    that never declared schemas still runs."""
    d = schema_dir or DEFAULT_DIR
    reg = {}
    if not os.path.isdir(d):
        return reg
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(d, name), encoding="utf-8") as f:
            decl = json.load(f)
        tag = decl.get("schema")
        if tag:
            reg[tag] = decl
    return reg


def _check_type(field, value, want):
    fn = _TYPES.get(want)
    if fn is None:
        return f"field {field!r}: unknown type {want!r} in declaration (expected one of {sorted(_TYPES)})"
    if not fn(value):
        return f"field {field!r}: expected type {want!r}, got {type(value).__name__}"
    return None


def validate(artifact, registry, expected=None):
    """Validate one artifact against a registry. Returns (ok, reason).

    `expected` is the tag the *edge* declares. A tag mismatch is the edge-type failure:
    upstream produced something this edge was not declared to carry.
    """
    tag = (artifact or {}).get("schema")
    if not tag:
        return False, "artifact has no 'schema' tag — an untyped artifact cannot travel a typed edge"
    if expected is not None and tag != expected:
        return False, f"edge declares schema {expected!r} but artifact is tagged {tag!r}"
    decl = registry.get(tag)
    if decl is None:
        # Never pass an unregistered tag: a typo would silently bypass type checking.
        return False, f"schema {tag!r} is not registered (known: {sorted(registry) or 'none'})"
    data = (artifact or {}).get("data")
    if not isinstance(data, dict):
        return False, f"schema {tag!r}: artifact 'data' must be an object, got {type(data).__name__}"
    missing = [k for k in decl.get("required", []) if k not in data]
    if missing:
        return False, f"schema {tag!r}: missing required fields: {missing}"
    for field, want in (decl.get("types") or {}).items():
        if field in data:
            err = _check_type(field, data[field], want)
            if err:
                return False, f"schema {tag!r}: {err}"
    return True, "ok"
