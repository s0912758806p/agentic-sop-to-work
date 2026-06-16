# SPDX-License-Identifier: MIT
"""Data model for plugin-forge. Pure dataclasses; no I/O."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Finding:
    id: str
    rule: str        # manifest|frontmatter|hooks|stdlib|tests
    severity: str    # HARD|SOFT
    plugin: str
    location: str
    detail: str


@dataclass
class LintReport:
    targets: List[str]
    hard: int
    soft: int
    findings: List[Finding] = field(default_factory=list)

    @property
    def clean(self):
        return self.hard == 0


@dataclass
class PluginSpec:
    name: str
    pkg: Optional[str] = None
    with_stop_hook: bool = False

    def __post_init__(self):
        if not self.pkg:
            self.pkg = self.name.replace("-", "").replace("_", "")
