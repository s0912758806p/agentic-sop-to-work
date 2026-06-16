#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plugin-forge lint CLI. Lint one plugin dir, or --all plugins in a marketplace.
Exits 1 if any HARD finding (the CI contract), else 0. SOFT/advisory never fail the build."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pluginforge import checks, report  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="plugin-forge — lint a Claude Code plugin / marketplace")
    ap.add_argument("target", nargs="?", help="a plugin directory (omit when using --all)")
    ap.add_argument("--all", action="store_true", help="lint every plugin in marketplace.json")
    ap.add_argument("--strict", action="store_true",
                    help="enable house invariants (stdlib-only, verify.py, test_no_third_party, ...)")
    ap.add_argument("--repo-root", default=".", help="repo root for --all (default: .)")
    a = ap.parse_args(argv)
    if a.all:
        rep = checks.run_lint(repo_root=a.repo_root, all_plugins=True, strict=a.strict)
    elif a.target:
        rep = checks.run_lint(plugin_dir=a.target, strict=a.strict)
    else:
        ap.error("provide a plugin directory, or --all")
    print(report.to_markdown(report.build(rep)))
    return 1 if rep.hard else 0


if __name__ == "__main__":
    sys.exit(main())
