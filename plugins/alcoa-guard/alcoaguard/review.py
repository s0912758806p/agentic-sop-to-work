# SPDX-License-Identifier: MIT
"""alcoa-guard CLI. FULL: --run-dir <kit run>. DEGRADED: --record <file> --contract <file>.
Exits 0 on success (findings never change the exit code — the HARD count lives in the report
for a human, and the v0.2 hook, to gate on); exits 2 if required arguments are missing."""
import argparse
import os
import sys
from datetime import date
from . import contract as contract_mod
from . import reader, checks, report


def run_degraded(record_path, contract_path, out_base=None, as_of=None):
    c = contract_mod.load(contract_path)
    rec = reader.read_degraded(record_path, c)
    verdict = checks.run_rules(rec, c, as_of=as_of)
    rep = report.build(verdict)
    out = out_base or os.path.join(os.getcwd(), ".alcoa-guard-runs", "degraded")
    jpath, mpath = report.write(rep, out)
    return rep, jpath, mpath


def run_full(run_dir, contract_path=None, out_base=None, as_of=None):
    rec, run_data = reader.read_full(run_dir)
    c = contract_mod.load(contract_path) if contract_path else contract_mod.infer_from_run(run_data)
    verdict = checks.run_rules(rec, c, as_of=as_of)
    rep = report.build(verdict)
    out = out_base or os.path.join(run_dir, ".alcoa-guard")
    jpath, mpath = report.write(rep, out)
    return rep, jpath, mpath


def _as_of(s):
    return date.fromisoformat(s) if s else None


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="alcoa-guard — deterministic ALCOA+ data-integrity linter")
    ap.add_argument("--run-dir", help="an agentic-sop-kit run dir (FULL mode)")
    ap.add_argument("--record", help="a record file: CSV or JSON (DEGRADED mode)")
    ap.add_argument("--contract", default=None, help="path to a .alcoa.json integrity contract")
    ap.add_argument("--out-base", default=None)
    ap.add_argument("--as-of", default=None, help="reference date YYYY-MM-DD for future-date checks")
    a = ap.parse_args(argv)
    as_of = _as_of(a.as_of)
    if a.run_dir:
        rep, jpath, mpath = run_full(a.run_dir, a.contract, a.out_base, as_of)
    elif a.record:
        if not a.contract:
            print("DEGRADED mode needs --contract <.alcoa.json>", file=sys.stderr)
            return 2
        rep, jpath, mpath = run_degraded(a.record, a.contract, a.out_base, as_of)
    else:
        ap.error("provide --run-dir <dir> (FULL) or --record <file> --contract <file> (DEGRADED)")
    print(report.to_markdown(rep))
    print(f"\n[alcoa-guard] wrote {mpath}")
    print(f"[alcoa-guard] wrote {jpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
