# GENERATED from shared/sopcore/cli.py by tools/sync_core.py — do not edit this copy; edit the source and re-run `python3 tools/sync_core.py`.
# sopcore-sha256: 9390933e2626b15d23fe894db88077b14f2977d8a988231595b347f933f679d3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The shared argparse skeleton: --run-dir (FULL mode) and --out-base, plus where output
lands when --out-base is not given: ${CLAUDE_PLUGIN_DATA}/<dirname> when Claude Code set it
(the plugin's persistent data dir, which survives plugin updates), else <cwd>/<dirname>."""
import os
import sys


def add_run_args(ap, out_base_help="output base dir",
                 run_dir_help="an agentic-sop-kit run dir (FULL mode)"):
    ap.add_argument("--run-dir", help=run_dir_help)
    ap.add_argument("--out-base", default=None, help=out_base_help)
    return ap


def data_dir():
    """${CLAUDE_PLUGIN_DATA} when set and non-empty, else None."""
    return os.environ.get("CLAUDE_PLUGIN_DATA") or None


def default_out_base(dirname):
    """Default output base: ${CLAUDE_PLUGIN_DATA}/<dirname>, else <cwd>/<dirname>."""
    return os.path.join(data_dir() or os.getcwd(), dirname)


def refuse(label, message):
    """Print an input refusal to stderr; return the CLI's usage-error exit code (2)."""
    print(f"[{label}] {message}", file=sys.stderr)
    return 2
