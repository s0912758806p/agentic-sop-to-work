# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The run-dir contract — the ONE reader definition of an agentic-sop-kit run dir.

The kit is the writer (kit/workflow/run.py writes run_manifest.json; kit/lib/kit.py writes
each step artifact as {schema, produced_by, data, trace}). Every companion reads a run
through this module and nothing else; tests/test_run_contract.py runs the real kit and reads
its output with this file, so writer and reader cannot drift silently.

Rules:
  • the run dir must hold run_manifest.json                      -> else NotAKitRun
  • only state == "OK_FOR_REVIEW" is reviewable; a FAILED (or state-less) run is refused
    with RunNotReviewable — a half-finished run must never be reviewed as if it finished
  • `branch→<goto>` manifest entries are routing records, not steps: they are skipped
  • an artifact path resolves as written when it exists (the kit writes absolute paths),
    else relative to the run dir, else by basename under the run dir (a shipped or
    relocated run dir)
  • the artifact that FEEDS the deliverable is final_output when that is JSON, else the
    last JSON step artifact; `produced_by` is that artifact's
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional

MANIFEST = "run_manifest.json"
OK_FOR_REVIEW = "OK_FOR_REVIEW"
BRANCH_PREFIX = "branch→"


class ContractError(Exception):
    """The run dir does not satisfy the contract."""


class NotAKitRun(ContractError):
    """No run_manifest.json — not an agentic-sop-kit run dir."""


class RunNotReviewable(ContractError):
    """The run did not finish in OK_FOR_REVIEW."""


@dataclass
class Step:
    skill: str
    ok: bool
    out: Optional[str]       # resolved path (may not exist)


@dataclass
class Artifact:
    path: str
    schema: Optional[str]
    produced_by: Optional[str]
    data: Any
    trace: List[dict] = field(default_factory=list)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise ContractError(f"unreadable JSON {path!r}: {e}")


def resolve(run_dir, p):
    if not p:
        return p
    if os.path.isabs(p) and os.path.exists(p):
        return p
    if not os.path.isabs(p):
        cand = os.path.join(run_dir, p)
        if os.path.exists(cand):
            return cand
    cand = os.path.join(run_dir, os.path.basename(p))
    return cand if os.path.exists(cand) else p


def read_artifact(path):
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ContractError(f"artifact {path!r} is not a JSON object")
    trace = raw.get("trace") or []
    return Artifact(path=path, schema=raw.get("schema"), produced_by=raw.get("produced_by"),
                    data=raw.get("data", {}), trace=[t for t in trace if isinstance(t, dict)])


@dataclass
class RunContract:
    run_dir: str
    manifest: dict
    run_id: Optional[str]
    flow: Optional[str]
    state: Optional[str]
    steps: List[Step]
    final_output: Optional[str]

    def json_artifacts(self):
        """Every existing JSON step artifact, once each (a revisit rewrites the same path),
        in first-seen order."""
        out, seen = [], set()
        for st in self.steps:
            p = st.out
            if not p or not str(p).endswith(".json") or not os.path.exists(p) or p in seen:
                continue
            seen.add(p)
            out.append(read_artifact(p))
        return out

    def pooled_trace(self):
        """The verbatim allow-set: every artifact's trace, deduped by (value, source, locator)."""
        out, seen = [], set()
        for art in self.json_artifacts():
            for t in art.trace:
                key = (str(t.get("value")), t.get("source"), t.get("locator"))
                if key not in seen:
                    seen.add(key)
                    out.append(t)
        return out

    def feeding_artifact(self):
        fo = self.final_output
        if fo and str(fo).endswith(".json") and os.path.exists(fo):
            return read_artifact(fo)
        last = None
        for st in self.steps:
            if st.out and str(st.out).endswith(".json") and os.path.exists(st.out):
                last = st.out
        return read_artifact(last) if last else None

    @property
    def produced_by(self):
        art = self.feeding_artifact()
        return art.produced_by if art else None


def load(run_dir):
    """Read and validate a run dir. Raises NotAKitRun / RunNotReviewable / ContractError."""
    mpath = os.path.join(run_dir, MANIFEST)
    if not os.path.exists(mpath):
        raise NotAKitRun(f"no {MANIFEST} in {run_dir!r} — not an agentic-sop-kit run dir")
    m = _read_json(mpath)
    if not isinstance(m, dict):
        raise ContractError(f"{MANIFEST} in {run_dir!r} is not a JSON object")
    state = m.get("state")
    if state != OK_FOR_REVIEW:
        where = f"; failed_step={m['failed_step']!r}" if m.get("failed_step") else ""
        raise RunNotReviewable(
            f"run {m.get('run_id')!r} is not reviewable: state={state!r}{where}. Only a run "
            f"that finished in {OK_FOR_REVIEW} is reviewed — fix and re-run it first (a partial "
            f"output can still be reviewed as a plain document in DEGRADED mode).")
    steps = [Step(skill=str(s.get("skill", "")), ok=bool(s.get("ok")), out=resolve(run_dir, s.get("out")))
             for s in (m.get("steps") or [])
             if isinstance(s, dict) and not str(s.get("skill", "")).startswith(BRANCH_PREFIX)]
    return RunContract(run_dir=run_dir, manifest=m, run_id=m.get("run_id"), flow=m.get("flow"),
                       state=state, steps=steps, final_output=resolve(run_dir, m.get("final_output")))
