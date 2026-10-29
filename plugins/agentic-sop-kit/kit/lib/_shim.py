# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""DEPRECATED (v1.11.0, removed in v2.0): kit/lib/ is now a set of re-export shims.

The engine moved to the `sopkit` package (kit/sopkit/). v1.10-style tool files still do

    sys.path.insert(0, ".../lib"); import kit

so each lib/<name>.py calls alias(): put the kit root on sys.path, import sopkit.<name>,
warn once with DeprecationWarning, and replace itself in sys.modules with the real module.

The warning is attributed to the shim module, not to the importing tool.py, so Python's
default filters keep it silent: a v1.10 tool's stderr — which the engine copies into the
manifest's step `error` — stays byte-identical. See it with `python3 -W default` or
PYTHONWARNINGS=default.
`import kit` therefore returns the very same module object as `from sopkit import kit`
(identical state, monkeypatching still works). New code: `from sopkit import kit`.
"""
import importlib
import os
import sys
import warnings

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def alias(name, submodules=()):
    if KIT_ROOT not in sys.path:
        sys.path.insert(0, KIT_ROOT)
    real = importlib.import_module("sopkit." + name)
    warnings.warn(f"`import {name}` from kit/lib/ is deprecated; use `from sopkit import {name}` "
                  f"(kit/lib/ shims are removed in v2.0)", DeprecationWarning, stacklevel=2)
    sys.modules[name] = real
    for sub in submodules:
        sys.modules[f"{name}.{sub}"] = getattr(real, sub)
    return real
