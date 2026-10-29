#!/usr/bin/env python3
# GENERATED from shared/sopcore/harness.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: d3ea6f737ffdf37e9ed4effa3c6cf98196b85781f05751811f543a906d87d087
# SPDX-License-Identifier: MIT
"""Regression runner — every unit + integration test must pass.

Each test file is self-contained (it puts the plugin root on sys.path), so we just run
them as subprocesses. One command for CI and humans:
    python3 tests/verify.py        # exit 0 = all green, 1 = something failed
"""
import glob
import os
import subprocess
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))


def main():
    files = sorted(glob.glob(os.path.join(TESTS, "test_*.py")))
    failed, ran = [], 0
    for f in files:
        r = subprocess.run([sys.executable, f], capture_output=True, text=True)
        last = (r.stderr.strip().splitlines() or [""])[-1]
        n = ""
        for ln in r.stderr.splitlines():
            if ln.startswith("Ran "):
                n = ln.split()[1]
        print(f"{'PASS' if r.returncode == 0 else 'FAIL'}  {os.path.basename(f):<30} ({n} tests)  {last if r.returncode else ''}")
        ran += int(n or 0)
        if r.returncode != 0:
            failed.append(os.path.basename(f))
            print(r.stdout)
            print(r.stderr)
    print(f"\n{len(files) - len(failed)}/{len(files)} files passed · {ran} tests total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
