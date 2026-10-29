# SPDX-License-Identifier: MIT
"""vendored-core-drift (HARD, always on): generated code must stay what was generated.

The companions vendor the suite's shared core as `<pkg>/_core/` and carry generated test /
hook files, all stamped by tools/sync_core.py with a content hash (see _core/vendor.py).
  • any stamped file whose content no longer matches its hash      -> hand-edited copy
  • when a repo above the plugin has shared/sopcore/: every `_core/` dir must hold exactly
    its modules with identical bodies                              -> stale or partial copy
The fix is never to edit the copy: edit shared/sopcore/, then run tools/sync_core.py."""
import glob
import os
from .._core import vendor
from ..model import Finding

RULE = "vendored-core-drift"
_SKIP_DIRS = {"__pycache__", "examples", ".pytest_cache"}
_FIX = "edit shared/sopcore/ and re-run `python3 tools/sync_core.py`"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _walk(plugin_dir):
    for root, dirs, files in os.walk(plugin_dir):
        dirs[:] = [x for x in dirs if x not in _SKIP_DIRS]
        yield root, dirs, files


def find_shared(plugin_dir):
    """The nearest <ancestor>/shared/sopcore above the plugin, or None (standalone)."""
    d = os.path.dirname(os.path.abspath(plugin_dir))
    while True:
        cand = os.path.join(d, "shared", "sopcore")
        if os.path.isfile(os.path.join(cand, "__init__.py")):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def check(plugin_dir, strict):
    name = os.path.basename(os.path.normpath(plugin_dir))
    findings, cores = [], []

    def hard(rel, detail):
        findings.append(Finding(f"{RULE}:{rel}", RULE, "HARD", name, rel, detail))

    for root, dirs, files in _walk(plugin_dir):
        if os.path.basename(root) == "_core":
            cores.append(root)
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                state = vendor.intact(_read(path))
            except (OSError, UnicodeDecodeError):
                continue
            if state is False:
                hard(os.path.relpath(path, plugin_dir),
                     f"generated file was edited (content no longer matches its stamp) — {_FIX}")

    shared = find_shared(plugin_dir)
    if not shared:
        return findings
    source = {}
    for p in glob.glob(os.path.join(shared, "*.py")):
        source[os.path.basename(p)] = _read(p).replace("\r\n", "\n")
    for core in sorted(cores):
        have = {os.path.basename(p) for p in glob.glob(os.path.join(core, "*.py"))}
        for fn in sorted(set(source) | have):
            rel = os.path.relpath(os.path.join(core, fn), plugin_dir)
            if fn not in have:
                hard(rel, f"missing vendored module shared/sopcore/{fn} — {_FIX}")
            elif fn not in source:
                hard(rel, f"stale vendored module: shared/sopcore/{fn} no longer exists — {_FIX}")
            elif vendor.unstamp(_read(os.path.join(core, fn)))[0] != source[fn]:
                hard(rel, f"out of date with shared/sopcore/{fn} — {_FIX}")
    return findings
