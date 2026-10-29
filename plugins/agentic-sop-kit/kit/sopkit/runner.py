# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""The run loop behind workflow/run.py: one RunContext, one manifest builder, one step loop.

Before v1.11.0 this was a ~290-line main() of closures over shared mutable state, with the
manifest dict rebuilt by hand in seven places. Now:

  RunContext       everything one execution owns (paths, counters, the walk so far)
  build_manifest   THE manifest exit — every state the runner reports goes through it
  preflight        refusals before anything runs (topology / already stalled / exhausted)
  step_loop        the walk itself: steps, gates, branches, bounded back-edges

The run-dir format is a contract (second-opinion / alcoa-guard read it): key ORDER in
each manifest shape is pinned by tests/integration/test_golden.py, which is why
build_manifest takes the shape-specific keys as ordered kwargs instead of a dict merge.

Exit codes: 0 = finished (DRAFT, OK_FOR_REVIEW); 2 = failed / refused. Every stop writes
run_manifest.json first, then raises SystemExit — nothing exits without a manifest.
"""
import json
import os
import shutil
import sys

from . import gates, graph, kit
from .console import safe_print
from .engine import run_step, substitute
from .flow import resolve_branch_case
from .loop import progress, state

BANNER = "DRAFT — 範例流程產出，需人員覆核；本 kit 永不自動歸檔進任何受控系統。"


class RunContext:
    """State of one execution of one flow under one run-id."""

    def __init__(self, flow, run, inp, *, max_fix_retries, stall_window, allow_mutations=False):
        self.flow = flow
        self.run = run
        self.rid = os.path.basename(run)
        self.inp = inp
        self.max_fix_retries = max_fix_retries
        self.stall_window = stall_window
        self.allow_mutations = allow_mutations

        self.manifest_path = os.path.join(run, "run_manifest.json")
        self.sig_path = os.path.join(run, ".fix_signatures")
        self.stalled_path = os.path.join(run, ".stalled")
        self.counter_path = os.path.join(run, ".fix_attempts")

        self.is_graph = graph.declares_graph(flow)
        _, _, self.name2idx, _ = graph.build(flow)
        self.node_names = []
        self.graph_keys = {}
        self.prev_failures = 0

        self.steps = []          # manifest `steps`, in execution order
        self.path_taken = []     # the walk actually performed (graph flows)
        self.visits = {}         # node index -> times run (back-edges cause re-runs)
        self.revisits = {}       # (from_index, to_index) -> back-edge traversals so far
        self.edge_sigs = {}      # (from_index, to_index) -> progress signatures on that edge
        self.last_out = None

    def resolve(self, value):
        return substitute(value, self.inp, self.run)

    def graph_extra(self):
        """Graph keys are added only when the flow opted in — a legacy flow's manifest keeps
        exactly its pre-graph key set (tests/integration/test_legacy_flow.py)."""
        if not self.is_graph:
            return {}
        return dict(self.graph_keys, path_taken=self.path_taken)

    def sig_history(self):
        try:
            with open(self.sig_path, encoding="utf-8") as f:
                return [ln.strip() for ln in f if ln.strip()]
        except OSError:
            return []

    def read_failures(self):
        if not os.path.exists(self.counter_path):
            return 0
        try:
            with open(self.counter_path, encoding="utf-8") as f:
                return int(f.read().strip() or "0")
        except ValueError:
            return 0

    def count_failure(self):
        """`.fix_attempts` holds FAILED executions only — a passing re-run is not a fix retry."""
        with open(self.counter_path, "w", encoding="utf-8") as f:
            f.write(str(self.prev_failures + 1))

    def mark_stalled(self, detail=" ｜ 無法寫入 stall marker"):
        try:
            open(self.stalled_path, "w", encoding="utf-8").close()
        except OSError as e:
            safe_print(f"  [WARN] could not write stall marker: {e}{detail}", file=sys.stderr)


def build_manifest(ctx, state_, *, graph_keys=True, tail=None, **extra):
    """The single manifest exit.

    Layout: flow, run_id, state, <extra in the caller's order>, human_review_required,
    banner, <tail>, <graph keys when the flow opted in and graph_keys is set>.
    """
    m = {"flow": ctx.flow["name"], "run_id": ctx.rid, "state": state_}
    m.update(extra)
    m["human_review_required"] = True
    m["banner"] = BANNER
    if tail:
        m.update(tail)
    if graph_keys:
        m.update(ctx.graph_extra())
    return m


def _halt(ctx, manifest, message, code=2):
    kit.write_artifact(manifest, ctx.manifest_path)
    for line in ([message] if isinstance(message, str) else message):
        safe_print(line)
    raise SystemExit(code)


def preflight(ctx):
    """Refuse before executing: illegal topology, an already-stalled run-id, an exhausted
    fix budget. Fills ctx's topology fields on the way."""
    # graph.analyze is the single authority, and the runtime enforces exactly what --plan
    # reports: an illegal topology refuses to run. One rule, no per-flow exceptions.
    hard, topo = graph.analyze(ctx.flow)
    if hard:
        _halt(ctx, build_manifest(
            ctx, "FAILED", graph_keys=False, topology_invalid=True, problems=hard,
            error="illegal topology — refused before executing ｜ 拓撲不合法，未執行即拒跑:\n  - "
                  + "\n  - ".join(hard)),
            ["  ⛔ illegal topology — nothing executed ｜ 拓撲不合法，未執行"] + [f"    - {m}" for m in hard])

    ctx.node_names = [n["name"] for n in topo["nodes"]]
    if ctx.is_graph:
        ctx.graph_keys = {"topology": {
            "nodes": ctx.node_names, "owners": topo["owners"],
            "back_edges": [{"frm": e["frm"], "to": e["to"], "max_revisits": e["max_revisits"]}
                           for e in topo["edges"] if e["back"]]}}

    # A previously-detected stall STOPS re-runs (decision A).
    if os.path.exists(ctx.stalled_path):
        _halt(ctx, build_manifest(
            ctx, "FAILED", graph_keys=False, stalled=True, stall_reason="already_stalled",
            error="run already marked stalled — no verifiable progress; STOP, human needed ｜ 已判定原地打轉，交人處理"),
            "  ⛔ stalled — STOP, human needed ｜ 原地打轉，交人")

    # Code-enforced fix-loop ceiling (per run-id). The /sop-flow Claude layer auto-fixes by
    # re-invoking with the SAME --run-id; past 1 + max_fix_retries FAILED executions the
    # run-id is refused — the real "封頂" lives in code, not in the prose of the command.
    ctx.prev_failures = ctx.read_failures()
    if ctx.prev_failures > ctx.max_fix_retries:
        _halt(ctx, build_manifest(
            ctx, "FAILED", graph_keys=False, fix_exhausted=True, attempts=ctx.prev_failures,
            max_fix_retries=ctx.max_fix_retries,
            error=f"fix-loop exhausted: {ctx.max_fix_retries} auto-fix retries used ｜ 自動修復已達上限，交人處理"),
            f"  ⛔ fix-loop exhausted ({ctx.max_fix_retries} retries) — STOP, human needed ｜ 自動修復達上限，交人")


def _fail(ctx, label, err, failure=None):
    """A step / branch failed. Turn it into a progress signature; no verifiable progress
    (idle / A→B→A thrash) is a STALL (decision A: also drop a .stalled marker so the next
    same-run-id call is refused); otherwise a plain FAILED manifest."""
    ctx.count_failure()
    attempt = ctx.prev_failures + 1
    if failure is not None:
        sig = progress.progress_signature(failure, run_dir=ctx.run)
        try:
            with open(ctx.sig_path, "a", encoding="utf-8") as sf:
                sf.write(sig + "\n")
        except OSError as e:
            safe_print(f"  [WARN] could not record stall signature: {e} ｜ 無法記錄 stall signature", file=sys.stderr)
        history = ctx.sig_history()
        verdict = progress.classify_progress(history, ctx.stall_window)
        if verdict:
            ctx.mark_stalled()
            _halt(ctx, build_manifest(
                ctx, "FAILED", stalled=True, stall_reason=verdict, failed_step=label,
                repeated_signature=sig, stall_rounds=len(history), stall_window=ctx.stall_window,
                failure=failure, fix_attempt=attempt, max_fix_retries=ctx.max_fix_retries,
                steps=ctx.steps,
                error=(f"stall detected ({verdict}): no verifiable progress over "
                       f"{len(history)} attempts — STOP, human needed ｜ 原地打轉，交人")),
                f"  ⛔ stall ({verdict}) — STOP, human needed ｜ 原地打轉，交人")
    _halt(ctx, build_manifest(
        ctx, "FAILED", failed_step=label, error=(err or "")[-1000:], steps=ctx.steps,
        failure=failure, fix_attempt=attempt, max_fix_retries=ctx.max_fix_retries),
        f"  ❌ step failed ｜ 步驟失敗： {(err or '')[:300]}")


def _stop_back_edge(ctx, kind, frm, goto, extra, message):
    """Deterministic early stop on a bounded back-edge (exhausted bound, or no progress).
    Never falls through to the next step: a capped loop STOPS and hands to a human."""
    ctx.count_failure()
    _halt(ctx, build_manifest(
        ctx, "FAILED", back_edge={"frm": frm, "to": goto, "max_revisits": extra.get("max_revisits")},
        steps=ctx.steps, error=message, tail=extra),
        f"  ⛔ {kind} on back-edge {frm}→{goto} — STOP, human needed ｜ 交人處理")


def _archive_previous(op, visit):
    """Keep the previous attempt when a bounded back-edge re-runs a node.

    Overwriting would destroy the retry history — and preserving it is the whole reason
    state stays in versioned artifacts instead of a central store that overwrites.
    """
    if visit <= 1 or not os.path.exists(op):
        return None
    stem, ext = os.path.splitext(op)
    archive = f"{stem}.visit{visit - 1}{ext}"
    try:
        os.replace(op, archive)
        return archive
    except OSError as e:
        safe_print(f"  [WARN] could not archive {op}: {e} ｜ 無法歸檔上一次產物", file=sys.stderr)
        return None


def _branch(ctx, i, st):
    """Route on a prior artifact. Returns the next step index."""
    node = ctx.node_names[i]
    art = ctx.resolve(st["branch"])

    def bfail(msg):
        return {"step": f"branch@{i}", "gate_type": None, "message": msg, "artifact": art}

    # A branch routes on a prior step's artifact. If that artifact is missing or unreadable
    # there is nothing to decide on: routing empty data through `default` would hide the
    # upstream fault, so it is a hard failure.
    try:
        data = kit.read_artifact(art).get("data", {})
    except (OSError, ValueError, AttributeError) as e:
        _fail(ctx, f"branch@{i}", f"branch: cannot read {art} ｜ 讀不到分支依據的產物：{e}",
              bfail(f"branch artifact unreadable: {e}"))
    case, why = resolve_branch_case(st.get("cases", []), data)
    goto = case.get("goto") if case is not None else None
    if goto is None:
        _fail(ctx, f"branch@{i}", f"branch: no usable case ｜ 無可用分支：{why}", bfail(why))
    if goto not in ctx.name2idx:
        _fail(ctx, f"branch@{i}", f"branch goto {goto!r}: no such step ｜ 指向不存在的步驟",
              bfail(f"goto {goto!r}: no such step"))
    target = ctx.name2idx[goto]
    ctx.visits[i] = ctx.visits.get(i, 0) + 1
    ctx.path_taken.append({"node": node, "visit": ctx.visits[i], "kind": "branch", "goto": goto})
    if target <= i:
        # A backward jump is legal ONLY as a declared, bounded back-edge. The static analyser
        # already refused an undeclared or unbounded one; this mirrors it at runtime so a
        # hand-edited flow cannot slip past.
        mr = case.get("max_revisits")
        if not (case.get("back") and graph.valid_bound(mr)):
            _fail(ctx, f"branch@{i}", f"branch goto {goto!r}: must be forward-only ｜ 必須往前",
                  bfail(f"goto {goto!r}: not forward-only"))
        key = (i, target)
        # Progress sensor, per edge: hash the routing state this edge is deciding on.
        # Identical state across revisits is genuine no-progress (idle), exactly as in the
        # fix-loop — measured from the artifact, never from a model's self-report.
        sig = progress.progress_signature(
            {"step": f"back-edge {node}->{goto}", "gate_type": None,
             "message": json.dumps(data, sort_keys=True, ensure_ascii=False)},
            run_dir=ctx.run)
        hist = ctx.edge_sigs.setdefault(key, [])
        hist.append(sig)
        verdict = progress.classify_progress(hist, ctx.stall_window)
        if verdict:
            ctx.mark_stalled(detail="")
            _stop_back_edge(
                ctx, f"stall ({verdict})", node, goto,
                {"stalled": True, "stall_reason": verdict, "repeated_signature": sig,
                 "stall_rounds": len(hist), "stall_window": ctx.stall_window, "max_revisits": mr},
                (f"stall detected ({verdict}) on back-edge {node}->{goto}: no verifiable "
                 f"progress over {len(hist)} revisit(s) — STOP, human needed ｜ 原地打轉，交人"))
        used = ctx.revisits.get(key, 0)
        if used >= mr:
            _stop_back_edge(
                ctx, "revisits exhausted", node, goto,
                {"revisit_exhausted": True, "revisits": used, "max_revisits": mr},
                (f"back-edge {node}->{goto} exhausted its bound: {mr} revisit(s) used "
                 f"— STOP, human needed ｜ 退回次數已達上限，交人處理"))
        ctx.revisits[key] = used + 1
        safe_print(f"  [BACK-EDGE] → {goto}  (revisit {used + 1}/{mr})")
    else:
        safe_print(f"  [BRANCH] → {goto}")
    ctx.steps.append({"skill": f"branch→{goto}", "ok": True, "out": art, "error": ""})
    return target


def _step_label(st):
    if st.get("skill"):
        return st["skill"]
    cmd = st.get("cmd", "")
    cmd = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    return "cmd: " + (cmd[:40] + ("…" if len(cmd) > 40 else ""))


def _execute(ctx, i, st):
    """Run one tool / cmd / map step plus its gate. Returns the next step index."""
    node = ctx.node_names[i]
    op = ctx.resolve(st["out"])
    ctx.visits[i] = ctx.visits.get(i, 0) + 1
    archived = _archive_previous(op, ctx.visits[i])
    ok, err = run_step(st, ctx.resolve, ctx.inp, ctx.allow_mutations, run=ctx.run)
    gate_type = None
    if ok and st.get("gate"):
        gate_type = st["gate"]["type"]
        ok2, gerr = gates.run_gate(gate_type, kit.read_artifact(op), st["gate"].get("args"))
        if not ok2:
            ok, err = False, f"gate {gate_type} failed ｜ 閘門未過: {gerr}"
    if ok and st.get("writes"):
        # Declared write-set fulfilment: a node that claims to write state fields must
        # actually leave a readable JSON artifact carrying a data object.
        try:
            if not isinstance(kit.read_artifact(op).get("data"), dict):
                ok, err = False, (f"declares writes={st['writes']} but its artifact has no "
                                  f"'data' object ｜ 宣告寫入卻沒有可讀的 data")
        except (OSError, ValueError) as e:
            ok, err = False, f"declares writes={st['writes']} but its artifact is unreadable: {e}"
    label = _step_label(st)
    ctx.steps.append({"skill": label, "ok": ok, "out": op, "error": (err or "")[:600]})
    entry = {"node": node, "visit": ctx.visits[i], "kind": "step", "out": op, "ok": ok}
    if archived:
        entry["archived_previous"] = archived
    ctx.path_taken.append(entry)
    safe_print(f"  [{'OK' if ok else 'FAIL'}] {label} → {op}"
               + (f"  (visit {ctx.visits[i]})" if ctx.visits[i] > 1 else ""))
    if not ok:
        _fail(ctx, label, err, {"step": label, "gate_type": gate_type,
                                "message": (err or "")[-1000:], "artifact": op})
    ctx.last_out = op
    return i + 1


def step_loop(ctx):
    """Walk the flow to completion. Raises SystemExit(0) with an OK_FOR_REVIEW manifest, or
    SystemExit(2) via _fail / _stop_back_edge."""
    safe_print(f"flow={ctx.flow['name']} run={ctx.rid} attempt={ctx.prev_failures + 1}")
    steps = ctx.flow["steps"]
    i = 0
    while i < len(steps):
        st = steps[i]
        i = _branch(ctx, i, st) if graph.kind(st) == "branch" else _execute(ctx, i, st)
    final = ctx.last_out
    _halt(ctx, build_manifest(ctx, "OK_FOR_REVIEW", steps=ctx.steps, final_output=final),
          [f"  ✅ 流程完成 → {final}", "  " + BANNER], code=0)


def count_run_dirs(base):
    if not os.path.isdir(base):
        return 0
    return sum(1 for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))


def prune_runs(base, keep_runs):
    if not os.path.isdir(base):
        safe_print("  (no runs dir — nothing to prune ｜ 無 runs 可清)")
        return 0
    entries = [(n, os.path.getmtime(os.path.join(base, n)))
               for n in os.listdir(base) if os.path.isdir(os.path.join(base, n))]
    evict = state.runs_to_evict(entries, keep_runs=keep_runs)
    removed = 0
    for rid in evict:
        p = os.path.join(base, rid)
        shutil.rmtree(p, ignore_errors=True)
        if os.path.exists(p):
            safe_print(f"  [WARN] could not prune {rid}: still present ｜ 無法清除", file=sys.stderr)
        else:
            removed += 1
    safe_print(f"  🧹 pruned {removed}/{len(evict)} run-dir(s); kept newest {min(len(entries), keep_runs)} ｜ 已清理舊 run")
    return 0
