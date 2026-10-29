# SPDX-License-Identifier: MIT
"""Deterministic recompute kernel — re-exports the suite's shared one (alcoaguard/_core/
arithmetic.py, vendored from shared/sopcore). Never raises. Since v0.2.0 a mismatch reason
reads "recomputed <op>=X vs stated Y" (it used to be just the op name), and count is exact
(a stated 3.7 no longer truncates to 3)."""
from ._core.arithmetic import recompute, reeval_verdict  # noqa: F401
