# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Second Opinion — domain-neutral, adversarial honesty reviewer for a DRAFT output.

Portable engine core (stdlib-only). It re-implements the agentic-sop-kit artifact
contract ({schema, produced_by, data, trace}) for READING only — it never imports the
kit. Two layers: deterministic honesty checks (this package) + a capped advisory LLM
pass (driven by the skill). The review report is itself a DRAFT; a human owns the verdict.
"""
