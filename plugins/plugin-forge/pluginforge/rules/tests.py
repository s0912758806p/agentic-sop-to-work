# SPDX-License-Identifier: MIT
"""Tier-1 (strict): the house test harness exists somewhere under the plugin
(verify.py + test_no_third_party.py). Location-flexible — the kit keeps them under
kit/tests/, the companions under tests/; both are fine. examples/ and __pycache__/ don't count."""
import glob
import os
from ..model import Finding

_REQUIRED = ("verify.py", "test_no_third_party.py")


def _has(plugin_dir, fname):
    for m in glob.glob(os.path.join(plugin_dir, "**", fname), recursive=True):
        parts = os.path.relpath(m, plugin_dir).split(os.sep)
        if len(parts) > 1 and "examples" not in parts and "__pycache__" not in parts:
            return True
    return False


def check(plugin_dir, strict):
    if not strict:
        return []
    name = os.path.basename(os.path.normpath(plugin_dir))
    findings = []
    for req in _REQUIRED:
        if not _has(plugin_dir, req):
            findings.append(Finding(f"tests:{req}", "tests", "HARD", name, f"**/{req}",
                                    f"missing {req} anywhere under the plugin"))
    return findings
