# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""CLI entry point for the DETERMINISTIC layer (zero-LLM).

    python3 -m secondop.review --run-dir <kit run_dir>        # FULL mode
    python3 -m secondop.review --doc <file> --inputs <...>    # DEGRADED mode (task 5)

It reads the draft, runs the deterministic checks, writes second_opinion.{json,md}, and
prints the human-readable report. It NEVER approves/rejects — the advisory LLM pass and
the human decision are driven by the /second-opinion command/skill on top of this.
"""
import argparse
import os
import sys

from . import checks, core, llm_contract, reader, report


def _emit(draft, out_base, label, advisory_path=None):
    det = checks.run_checks(draft)
    out_base = out_base or os.path.join(os.getcwd(), ".second-opinion-runs")
    out_dir = os.path.join(out_base, draft.run_id or label)
    # Always (re)write the envelope so the /second-opinion command can drive the LLM pass.
    core.write_json(llm_contract.build_llm_envelope(draft, det),
                    os.path.join(out_dir, "llm_input.json"))

    advisory, dropped = [], []
    cap = llm_contract.max_passes()
    llm_meta = {"passes_used": llm_contract.passes_used(out_dir), "max_passes": cap, "capped": False}
    if advisory_path:
        if llm_contract.passes_used(out_dir) >= cap:
            llm_meta["capped"] = True
        else:
            used = llm_contract.bump_passes(out_dir)
            candidates = core.read_json(advisory_path).get("findings", [])
            settled = {f.settled_key for f in det if f.settled_key}
            advisory, dropped = llm_contract.merge_llm_findings(candidates, draft.raw_text, settled)
            llm_meta = {"passes_used": used, "max_passes": cap, "capped": False}

    rep = report.build(draft, det + advisory, llm=llm_meta, dropped=dropped)
    jpath, mpath = report.write(rep, out_dir)
    return rep, jpath, mpath


def run_full(run_dir, out_base=None, advisory_path=None):
    return _emit(reader.read_full(run_dir), out_base, "review", advisory_path)


def run_degraded(doc_path, inputs_paths, out_base=None, advisory_path=None):
    return _emit(reader.read_degraded(doc_path, inputs_paths), out_base,
                 "review-degraded", advisory_path)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Second Opinion — deterministic honesty review (zero-LLM)")
    ap.add_argument("--run-dir", help="an agentic-sop-kit run_dir (FULL mode)")
    ap.add_argument("--doc", help="a plain document (DEGRADED mode)")
    ap.add_argument("--inputs", nargs="*", default=None, help="source inputs for DEGRADED mode")
    ap.add_argument("--out-base", default=None, help="output base dir (default ./.second-opinion-runs)")
    ap.add_argument("--advisory", default=None,
                    help="path to the LLM's candidate findings JSON (folds the capped advisory pass in)")
    a = ap.parse_args(argv)

    if a.run_dir:
        if not os.path.exists(os.path.join(a.run_dir, "run_manifest.json")):
            print(f"no run_manifest.json in {a.run_dir!r} — for a plain document use "
                  f"--doc … --inputs …", file=sys.stderr)
            return 2
        rep, jpath, mpath = run_full(a.run_dir, a.out_base, a.advisory)
    elif a.doc:
        if not a.inputs:
            print("DEGRADED mode needs --inputs <file...> (the sources to check claims "
                  "against).", file=sys.stderr)
            return 2
        rep, jpath, mpath = run_degraded(a.doc, a.inputs, a.out_base, a.advisory)
    else:
        ap.error("provide --run-dir <dir> (FULL) or --doc <file> --inputs <...> (DEGRADED)")

    print(report.to_markdown(rep))
    print(f"\n[second-opinion] wrote {mpath}")
    print(f"[second-opinion] wrote {jpath}")
    # Advisory tool: always exit 0. The HARD count is in the report for a human/hook to gate on.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
