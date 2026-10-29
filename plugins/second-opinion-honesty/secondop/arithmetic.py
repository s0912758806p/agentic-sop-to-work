# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Deterministic re-derivation: recompute aggregates + re-evaluate spec verdicts.

Re-exports the shared kernel (secondop/_core/arithmetic.py, vendored from shared/sopcore) so
`from secondop import arithmetic` keeps working. Since v0.3.0 the semantics are the suite's:
an empty list fails sum/mean/min/max (mean used to return 0.0), sums use math.fsum, and a
mismatch reads "recomputed <op>=X vs stated Y".
"""
from ._core.arithmetic import recompute, reeval_verdict  # noqa: F401
