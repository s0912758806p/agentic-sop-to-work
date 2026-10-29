#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Vendor the shared core into every companion plugin, and generate their shared harness.

    python3 tools/sync_core.py           # write: shared/sopcore/ -> plugins/<p>/<pkg>/_core/
    python3 tools/sync_core.py --check   # CI: exit 1 on any drift, write nothing

For each companion in COMPANIONS it writes
  <pkg>/_core/<module>.py        every shared/sopcore/*.py, stamped GENERATED (+ content hash)
  tests/verify.py                \
  tests/test_no_third_party.py    > rendered from shared/sopcore/harness.py, stamped GENERATED
  hooks/session_check.py         /
and deletes stale modules from <pkg>/_core/. Vendoring (not a cross-plugin import) is what
lets each plugin install standalone. agentic-sop-kit is NOT a consumer: it WRITES the run-dir
contract; tests/test_run_contract.py binds the two sides instead.
"""
import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "shared", "sopcore")
sys.path.insert(0, os.path.join(ROOT, "shared"))
from sopcore import harness, vendor  # noqa: E402

# plugin dir -> (python package, log label, module the SessionStart check imports)
COMPANIONS = {
    "second-opinion-honesty": ("secondop", "second-opinion", "secondop.review"),
    "alcoa-guard": ("alcoaguard", "alcoa-guard", "alcoaguard.review"),
    "plugin-forge": ("pluginforge", "plugin-forge", "pluginforge.lint"),
}


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def expected():
    """{absolute path: exact text} for every generated file."""
    core = {os.path.basename(p): _read(p) for p in sorted(glob.glob(os.path.join(CORE, "*.py")))}
    out = {}
    for plugin, (pkg, label, probe) in COMPANIONS.items():
        pdir = os.path.join(ROOT, "plugins", plugin)
        for name, src in core.items():
            out[os.path.join(pdir, pkg, "_core", name)] = vendor.stamp(src, "shared/sopcore/" + name)
        for rel, tmpl in harness.FILES.items():
            body = harness.render(tmpl, pkg, label, probe)
            out[os.path.join(pdir, *rel.split("/"))] = vendor.stamp(body, "shared/sopcore/harness.py")
    return out


def stale():
    """Modules in a <pkg>/_core/ that no longer exist in shared/sopcore/."""
    want = {os.path.basename(p) for p in glob.glob(os.path.join(CORE, "*.py"))}
    out = []
    for plugin, (pkg, _, _) in COMPANIONS.items():
        for p in glob.glob(os.path.join(ROOT, "plugins", plugin, pkg, "_core", "*.py")):
            if os.path.basename(p) not in want:
                out.append(p)
    return sorted(out)


def drift():
    problems = []
    for path, text in expected().items():
        rel = os.path.relpath(path, ROOT)
        if not os.path.exists(path):
            problems.append(f"missing  {rel}")
        elif _read(path).replace("\r\n", "\n") != text:
            problems.append(f"differs  {rel}")
    problems += [f"stale    {os.path.relpath(p, ROOT)}" for p in stale()]
    return problems


def write():
    changed = []
    for path, text in expected().items():
        if os.path.exists(path) and _read(path).replace("\r\n", "\n") == text:
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        changed.append(os.path.relpath(path, ROOT))
    for p in stale():
        os.remove(p)
        changed.append(os.path.relpath(p, ROOT) + " (removed)")
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description="vendor shared/sopcore into each companion plugin")
    ap.add_argument("--check", action="store_true", help="report drift and exit 1; write nothing")
    a = ap.parse_args(argv)
    if a.check:
        problems = drift()
        for p in problems:
            print(p)
        if problems:
            print(f"\n{len(problems)} file(s) drifted from shared/sopcore — edit shared/sopcore, "
                  f"then run: python3 tools/sync_core.py", file=sys.stderr)
            return 1
        print(f"sopcore in sync across {len(COMPANIONS)} companion plugins")
        return 0
    changed = write()
    for c in changed:
        print(f"wrote {c}")
    print(f"{len(changed)} file(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
