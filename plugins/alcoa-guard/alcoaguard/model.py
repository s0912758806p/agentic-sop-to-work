# SPDX-License-Identifier: MIT
"""Data model for alcoa-guard. Pure dataclasses; no I/O."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Entry:
    field: str
    value: Any
    author: Optional[str] = None
    timestamp: Optional[str] = None     # ISO-8601 string
    kind: str = "text"                  # text|number|date|id


@dataclass
class Record:
    fields: Dict[str, Any] = field(default_factory=dict)
    entries: List[Entry] = field(default_factory=list)
    raw_text: str = ""
    mode: str = "DEGRADED"              # FULL|DEGRADED
    source: str = ""


@dataclass
class IntegrityContract:
    required_fields: List[str] = field(default_factory=list)
    date_fields: List[str] = field(default_factory=list)
    date_order: List[List[str]] = field(default_factory=list)   # [[earlier, later], ...]
    no_future: bool = False
    attribution: List[str] = field(default_factory=list)        # fields needing author+timestamp
    id_patterns: Dict[str, str] = field(default_factory=dict)   # field -> regex
    units: Dict[str, str] = field(default_factory=dict)         # field -> expected unit token
    limits: Dict[str, Dict[str, float]] = field(default_factory=dict)   # field -> {lo, hi}
    aggregates: List[Dict[str, Any]] = field(default_factory=list)      # {op, over, stated}
    expected_set: Dict[str, List[str]] = field(default_factory=dict)    # field -> required members


@dataclass
class Finding:
    id: str
    principle: str       # attributable|contemporaneous|complete|accurate|consistent
    severity: str        # HARD|SOFT
    origin: str          # deterministic|human_judgment
    location: str
    detail: str
    evidence: str = ""


@dataclass
class Verdict:
    mode: str
    hard: int
    soft: int
    human_items: int
    findings: List[Finding] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)
    human_owns_verdict: bool = True
