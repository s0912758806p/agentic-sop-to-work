# SPDX-License-Identifier: MIT
"""Tier-1 (strict): the house test harness is present (verify.py + test_no_third_party.py)."""
import os
from ..model import Finding

_REQUIRED = ("verify.py", "test_no_third_party.py")


def check(plugin_dir, strict):
    if not strict:
        return []
    name = os.path.basename(os.path.normpath(plugin_dir))
    findings = []
    for req in _REQUIRED:
        if not os.path.exists(os.path.join(plugin_dir, "tests", req)):
            findings.append(Finding(f"tests:{req}", "tests", "HARD", name, f"tests/{req}",
                                    f"missing tests/{req}"))
    return findings
