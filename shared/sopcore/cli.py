# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The shared argparse skeleton: --run-dir (FULL mode) and --out-base, plus where output
lands when --out-base is not given."""
import os
import sys


def add_run_args(ap, out_base_help="output base dir",
                 run_dir_help="an agentic-sop-kit run dir (FULL mode)"):
    ap.add_argument("--run-dir", help=run_dir_help)
    ap.add_argument("--out-base", default=None, help=out_base_help)
    return ap


def default_out_base(dirname):
    """Default output base: <cwd>/<dirname>."""
    return os.path.join(os.getcwd(), dirname)


def refuse(label, message):
    """Print an input refusal to stderr; return the CLI's usage-error exit code (2)."""
    print(f"[{label}] {message}", file=sys.stderr)
    return 2
