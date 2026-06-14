# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Internal data model. One normalized representation (NormalizedDraft) feeds the
deterministic checks regardless of FULL/DEGRADED mode; mode only changes a finding's
severity/confidence. `sources` are kept as plain dicts in the kit trace shape
({value, source, locator}) so core.is_sourced / nearest_token consume them directly.
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Claim:
    """An asserted value in the DRAFT that can be checked against the sources."""
    id: str
    value: Any
    label: Optional[str] = None
    location: str = ""
    kind: str = "value"          # value | number | identifier | placeholder
    sourced: Optional[bool] = None


@dataclass
class Aggregate:
    """A re-derivable claim: op over a list vs a stated total."""
    id: str
    op: str                      # count | sum | mean | min | max
    over: List[Any] = field(default_factory=list)
    stated: Any = None
    stated_locator: str = ""
    over_locator: str = ""


@dataclass
class Verdict:
    """A PASS/FAIL / in-spec conclusion to re-evaluate against limits."""
    id: str
    text: str                    # the verdict word as written, e.g. "PASS" / "符合"
    polarity: str                # normalized: pass | fail | unknown
    measured: Optional[float] = None
    lo: Optional[float] = None
    hi: Optional[float] = None
    locator: str = ""
    label: Optional[str] = None


@dataclass
class Finding:
    """One honesty defect. severity HARD only ever comes from the deterministic layer
    in FULL mode; the advisory LLM layer is clamped to SOFT (see llm_contract)."""
    id: str
    vector: str                  # "#1" | "#2" | "#3" | "#4"
    severity: str                # HARD | SOFT
    origin: str                  # deterministic | advisory
    location: str
    claim: str
    evidence: str
    mode_confidence: float
    settled_key: str = ""        # canonical slot key used to suppress LLM re-flagging
    suggested_fix: Optional[str] = None


@dataclass
class NormalizedDraft:
    mode: str                                       # FULL | DEGRADED
    sources: List[dict] = field(default_factory=list)   # kit trace shape dicts
    claims: List[Claim] = field(default_factory=list)
    aggregates: List[Aggregate] = field(default_factory=list)
    verdicts: List[Verdict] = field(default_factory=list)
    raw_text: str = ""
    run_id: Optional[str] = None
    produced_by: Optional[str] = None
    draft_path: Optional[str] = None
    notes: List[str] = field(default_factory=list)
