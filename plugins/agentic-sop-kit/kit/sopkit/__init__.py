# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""sopkit — the agentic-sop-kit engine as one package (v1.11.0+).

Modules use relative imports only, so the package needs exactly one thing on sys.path:
the kit root (the directory holding sopkit/). Scripts in the kit root get that for free;
scripts deeper in the tree (workflow/run.py, skills/*/tool.py, tests/**) insert the kit
root once. kit/lib/*.py remain as deprecated re-export shims for v1.10-style
`sys.path.insert(..., "lib"); import kit` tool files — removed in v2.0.

    kit      artifact I/O, deps, run dirs, copy rule        config   every SOPKIT_* knob
    graph    static topology (the single authority)         flow     branch predicates
    gates    deterministic per-step gates                   schema   typed-edge registry
    engine   step executors + --plan                        runner   the run loop + manifest
    console  safe_print for non-UTF-8 consoles              loop/    progress · health · state
"""
