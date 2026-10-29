# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The GENERATED stamp on every vendored / generated file — written by tools/sync_core.py,
verified by plugin-forge's `vendored-core-drift` rule.

A stamped file carries two header lines (after a shebang, if any):
    # GENERATED from <source> by tools/sync_core.py — do not edit this copy; ...
    # sopcore-sha256: <sha256 of the file with these two lines removed>
so a hand-edited copy is detectable from the file alone, with no access to the source tree.
Line endings are normalized to \\n before hashing (a CRLF checkout is not drift).
"""
import hashlib

MARK = "# GENERATED from "
HASH = "# sopcore-sha256: "


def _norm(text):
    return text.replace("\r\n", "\n")


def digest(body):
    return hashlib.sha256(_norm(body).encode("utf-8")).hexdigest()


def stamp(body, source):
    body = _norm(body)
    header = [MARK + source + " by tools/sync_core.py — do not edit this copy; "
              "edit the source and re-run `python3 tools/sync_core.py`.",
              HASH + digest(body)]
    lines = body.split("\n")
    at = 1 if lines and lines[0].startswith("#!") else 0
    return "\n".join(lines[:at] + header + lines[at:])


def unstamp(text):
    """(body, recorded_digest), or (text, None) when the file carries no stamp."""
    lines = _norm(text).split("\n")
    head = lines[:3]
    if not any(ln.startswith(MARK) for ln in head):
        return text, None
    recorded = next((ln[len(HASH):].strip() for ln in head if ln.startswith(HASH)), "")
    keep = [ln for i, ln in enumerate(lines)
            if not (i < 3 and (ln.startswith(MARK) or ln.startswith(HASH)))]
    return "\n".join(keep), recorded


def is_stamped(text):
    return unstamp(text)[1] is not None


def intact(text):
    """True if stamped and unmodified, False if stamped and edited, None if not stamped."""
    body, recorded = unstamp(text)
    if recorded is None:
        return None
    return recorded == digest(body)
