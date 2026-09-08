# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Agentic Workflow 編排層：依 flow.json 的順序串接各 skill；run-scoped manifest；人核准 STOP。
步驟執行器在 lib/engine.py（run_step / run_map / print_plan）。退出碼：0 = 完成（DRAFT）；2 = 失敗。

失敗時 manifest 帶機器可讀 `failure{step,gate_type,message,artifact}`，供上層定向修復。
`--max-fix-retries N`（預設讀 `SOPKIT_MAX_FIX_RETRIES`、否則 3；與 Stop-hook 回歸共用同一上限）對同一 `--run-id` 封頂自動修復重試：這支引擎只負責**程式強制的上限**
——同一 run-id 執行超過 1+N 次即拒跑、寫 `fix_exhausted`；實際的修復（重生/改輸入）由 `/sop-flow`
的 Claude 層執行，引擎本身維持零 LLM、確定性。"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import kit  # noqa: E402
import gates  # noqa: E402
from flow import resolve_branch_case  # noqa: E402
from engine import run_step, print_plan  # noqa: E402
import graph  # noqa: E402
from loop import progress, state  # noqa: E402

FLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow.json")
BANNER = "DRAFT — 範例流程產出，需人員覆核；本 kit 永不自動歸檔進任何受控系統。"


def _declares_graph(flow):
    """True when the flow opts into graph features. Absent every one of these, the engine
    behaves exactly as it did before Graph Engineering (see tests/integration/test_legacy_flow.py)."""
    for st in flow.get("steps") or []:
        if st.get("reads") or st.get("writes"):
            return True
        if ((st.get("gate") or {}).get("args") or {}).get("schema_ref"):
            return True
        for c in st.get("cases") or []:
            if c.get("back"):
                return True
    return False


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
        print(f"  [WARN] could not archive {op}: {e} ｜ 無法歸檔上一次產物", file=sys.stderr)
        return None


def _keep_runs():
    return int(os.environ.get("SOPKIT_STATE_KEEP_RUNS", "20"))


def _count_run_dirs(base):
    if not os.path.isdir(base):
        return 0
    return sum(1 for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))


def _prune_runs(base, keep_runs):
    if not os.path.isdir(base):
        print("  (no runs dir — nothing to prune ｜ 無 runs 可清)")
        return 0
    entries = [(n, os.path.getmtime(os.path.join(base, n)))
               for n in os.listdir(base) if os.path.isdir(os.path.join(base, n))]
    evict = state.runs_to_evict(entries, keep_runs=keep_runs)
    removed = 0
    for rid in evict:
        p = os.path.join(base, rid)
        shutil.rmtree(p, ignore_errors=True)
        if os.path.exists(p):
            print(f"  [WARN] could not prune {rid}: still present ｜ 無法清除", file=sys.stderr)
        else:
            removed += 1
    print(f"  🧹 pruned {removed}/{len(evict)} run-dir(s); kept newest {min(len(entries), keep_runs)} ｜ 已清理舊 run")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="agentic-sop-kit workflow runner")
    ap.add_argument("--flow", default=FLOW, help="flow.json path (default: bundled demo flow)")
    ap.add_argument("--input", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out-base", default=None)
    ap.add_argument("--plan", action="store_true", help="list operations (and validate) without executing")
    ap.add_argument("--graph", action="store_true",
                    help="render the topology as Mermaid from the flow and exit; executes nothing")
    ap.add_argument("--allow-mutations", action="store_true", help="authorize steps marked mutates:true")
    ap.add_argument("--max-fix-retries", type=int, default=int(os.environ.get("SOPKIT_MAX_FIX_RETRIES", "3")),
                    help="code-enforced ceiling on auto-fix re-runs per --run-id (default: $SOPKIT_MAX_FIX_RETRIES or 3, shared with the Stop-hook regression loop); "
                         "the fixing itself is done by the /sop-flow Claude layer, not here")
    ap.add_argument("--stall-window", type=int, default=int(os.environ.get("SOPKIT_STALL_WINDOW", "2")),
                    help="stall early-stop: how many consecutive identical failure signatures count as "
                         "'no progress' (default: $SOPKIT_STALL_WINDOW or 2; 0 disables; cycle cap fixed at 2). "
                         "Deterministic, zero-LLM — complements the budget ceiling.")
    ap.add_argument("--prune", action="store_true",
                    help="evict run dirs beyond SOPKIT_STATE_KEEP_RUNS (newest kept); deletes — human-authorized")
    a = ap.parse_args(argv)

    base = a.out_base or kit.kit_path("runs")
    if a.prune:
        raise SystemExit(_prune_runs(base, _keep_runs()))

    with open(a.flow, encoding="utf-8") as f:
        flow = json.load(f)

    if a.graph:
        print(graph.mermaid(flow))
        raise SystemExit(0)

    _n = _count_run_dirs(base)
    if _n > _keep_runs():
        print(f"  ℹ️ {_n} run-dirs (keep {_keep_runs()}); {_n - _keep_runs()} prunable — run with --prune ｜ 可清舊 run")

    if a.plan:
        raise SystemExit(print_plan(flow, a.stall_window))

    inp = a.input or kit.kit_path(flow["input_default"])
    run = kit.run_dir(a.out_base, a.run_id)
    rid = os.path.basename(run)

    def resolve(v):
        return v.replace("$INPUT", inp).replace("$RUN", run)

    # --- pre-run topology gate ----------------------------------------------
    # graph.analyze is the single authority, and the runtime enforces exactly what --plan
    # reports: an illegal topology refuses to run. One rule, no per-flow exceptions.
    is_graph = _declares_graph(flow)
    hard, topo = graph.analyze(flow)
    if hard:
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED",
                "topology_invalid": True, "problems": hard,
                "error": "illegal topology — refused before executing ｜ 拓撲不合法，未執行即拒跑:\n  - "
                         + "\n  - ".join(hard),
                "human_review_required": True, "banner": BANNER}
        kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
        print("  ⛔ illegal topology — nothing executed ｜ 拓撲不合法，未執行")
        for msg in hard:
            print(f"    - {msg}")
        raise SystemExit(2)

    node_names = [n["name"] for n in topo["nodes"]]
    graph_keys = {}
    if is_graph:
        graph_keys = {"topology": {
            "nodes": node_names, "owners": topo["owners"],
            "back_edges": [{"frm": e["frm"], "to": e["to"], "max_revisits": e["max_revisits"]}
                           for e in topo["edges"] if e["back"]]}}

    # --- stall-detection state (per run-id; mirrors .fix_attempts) -----------
    sig_path = os.path.join(run, ".fix_signatures")
    stalled_path = os.path.join(run, ".stalled")

    def _sig_history():
        try:
            with open(sig_path, encoding="utf-8") as f:
                return [ln.strip() for ln in f if ln.strip()]
        except OSError:
            return []

    # Hard pre-run refusal: a previously-detected stall STOPS re-runs (decision A).
    if os.path.exists(stalled_path):
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "stalled": True,
                "stall_reason": "already_stalled",
                "error": "run already marked stalled — no verifiable progress; STOP, human needed ｜ 已判定原地打轉，交人處理",
                "human_review_required": True, "banner": BANNER}
        kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
        print("  ⛔ stalled — STOP, human needed ｜ 原地打轉，交人")
        raise SystemExit(2)

    # --- code-enforced fix-loop ceiling (per run-id) -------------------------
    # The /sop-flow Claude layer auto-fixes by re-invoking with the SAME --run-id.
    # This counter caps total executions at 1 + max_fix_retries and refuses past it
    # — the real "封頂" lives in code, not in the prose of the command.
    counter_path = os.path.join(run, ".fix_attempts")
    prev = 0
    if os.path.exists(counter_path):
        try:
            prev = int(open(counter_path, encoding="utf-8").read().strip() or "0")
        except ValueError:
            prev = 0
    if prev > a.max_fix_retries:
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED",
                "fix_exhausted": True, "attempts": prev, "max_fix_retries": a.max_fix_retries,
                "error": f"fix-loop exhausted: {a.max_fix_retries} auto-fix retries used ｜ 自動修復已達上限，交人處理",
                "human_review_required": True, "banner": BANNER}
        kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
        print(f"  ⛔ fix-loop exhausted ({a.max_fix_retries} retries) — STOP, human needed ｜ 自動修復達上限，交人")
        raise SystemExit(2)
    with open(counter_path, "w", encoding="utf-8") as cf:
        cf.write(str(prev + 1))

    print(f"flow={flow['name']} run={rid} attempt={prev + 1}")

    name2idx = {}
    for idx, st in enumerate(flow["steps"]):
        key = st.get("id") or st.get("skill")
        if key and key not in name2idx:
            name2idx[key] = idx

    steps = []
    last_out = None
    visits = {}        # node index -> how many times it has run (back-edges cause re-runs)
    revisits = {}      # (from_index, to_index) -> back-edge traversals so far
    edge_sigs = {}     # (from_index, to_index) -> progress signatures seen on that edge
    path_taken = []    # the walk actually performed, in order

    def _graph_extra():
        """Graph keys are added only when the flow opted in — a legacy flow's manifest
        keeps exactly its pre-graph key set (tests/integration/test_legacy_flow.py)."""
        if not is_graph:
            return {}
        return dict(graph_keys, path_taken=path_taken)

    def _fail(label, err, failure=None):
        # Stall detection: turn the failure into a progress signature, append to the per-run
        # history, and if there is no verifiable progress (idle / A→B→A thrash) STOP as a stall
        # (decision A: also drop a .stalled marker so the next same-run-id call is refused).
        if failure is not None:
            sig = progress.progress_signature(failure, run_dir=run)
            try:
                with open(sig_path, "a", encoding="utf-8") as sf:
                    sf.write(sig + "\n")
            except OSError as e:
                print(f"  [WARN] could not record stall signature: {e} ｜ 無法記錄 stall signature", file=sys.stderr)
            history = _sig_history()
            verdict = progress.classify_progress(history, a.stall_window)
            if verdict:
                try:
                    open(stalled_path, "w", encoding="utf-8").close()
                except OSError as e:
                    print(f"  [WARN] could not write stall marker: {e} ｜ 無法寫入 stall marker", file=sys.stderr)
                mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "stalled": True,
                        "stall_reason": verdict, "failed_step": label, "repeated_signature": sig,
                        "stall_rounds": len(history), "stall_window": a.stall_window, "failure": failure,
                        "fix_attempt": prev + 1, "max_fix_retries": a.max_fix_retries, "steps": steps,
                        "error": (f"stall detected ({verdict}): no verifiable progress over "
                                  f"{len(history)} attempts — STOP, human needed ｜ 原地打轉，交人"),
                        "human_review_required": True, "banner": BANNER, **_graph_extra()}
                kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
                print(f"  ⛔ stall ({verdict}) — STOP, human needed ｜ 原地打轉，交人")
                raise SystemExit(2)
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "failed_step": label,
                "error": (err or "")[-1000:], "steps": steps,
                "failure": failure, "fix_attempt": prev + 1, "max_fix_retries": a.max_fix_retries,
                "human_review_required": True, "banner": BANNER, **_graph_extra()}
        kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
        print("  ❌ step failed ｜ 步驟失敗：", (err or "")[:300])
        raise SystemExit(2)

    def _stop_back_edge(kind, frm, goto, extra, message):
        """Deterministic early stop on a bounded back-edge (exhausted bound, or no progress).
        Never falls through to the next step: a capped loop STOPS and hands to a human."""
        edge = {"frm": frm, "to": goto, "max_revisits": extra.get("max_revisits")}
        mani = {"flow": flow["name"], "run_id": rid, "state": "FAILED", "back_edge": edge,
                "steps": steps, "error": message, "human_review_required": True,
                "banner": BANNER, **extra, **_graph_extra()}
        kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
        print(f"  ⛔ {kind} on back-edge {frm}→{goto} — STOP, human needed ｜ 交人處理")
        raise SystemExit(2)

    i, n = 0, len(flow["steps"])
    while i < n:
        st = flow["steps"][i]
        node = node_names[i]
        if "branch" in st:
            art = resolve(st["branch"])
            data = kit.read_artifact(art).get("data", {}) if os.path.exists(art) else {}
            case, why = resolve_branch_case(st.get("cases", []), data)
            goto = case.get("goto") if case is not None else None
            bfail = lambda msg: {"step": f"branch@{i}", "gate_type": None, "message": msg, "artifact": art}
            if goto is None:
                _fail(f"branch@{i}", f"branch: no usable case ｜ 無可用分支：{why}", bfail(why))
            if goto not in name2idx:
                _fail(f"branch@{i}", f"branch goto {goto!r}: no such step ｜ 指向不存在的步驟",
                      bfail(f"goto {goto!r}: no such step"))
            target = name2idx[goto]
            visits[i] = visits.get(i, 0) + 1
            path_taken.append({"node": node, "visit": visits[i], "kind": "branch", "goto": goto})
            if target <= i:
                # A backward jump is legal ONLY as a declared, bounded back-edge. The static
                # analyser already refused an undeclared or unbounded one; this mirrors it at
                # runtime so a hand-edited flow cannot slip past.
                mr = case.get("max_revisits")
                if not (case.get("back") and isinstance(mr, int) and not isinstance(mr, bool) and mr >= 1):
                    _fail(f"branch@{i}", f"branch goto {goto!r}: must be forward-only ｜ 必須往前",
                          bfail(f"goto {goto!r}: not forward-only"))
                key = (i, target)
                # Progress sensor, per edge: hash the routing state this edge is deciding on.
                # Identical state across revisits is genuine no-progress (idle), exactly as in
                # the fix-loop — measured from the artifact, never from a model's self-report.
                sig = progress.progress_signature(
                    {"step": f"back-edge {node}->{goto}", "gate_type": None,
                     "message": json.dumps(data, sort_keys=True, ensure_ascii=False)},
                    run_dir=run)
                hist = edge_sigs.setdefault(key, [])
                hist.append(sig)
                verdict = progress.classify_progress(hist, a.stall_window)
                if verdict:
                    try:
                        open(stalled_path, "w", encoding="utf-8").close()
                    except OSError as e:
                        print(f"  [WARN] could not write stall marker: {e}", file=sys.stderr)
                    _stop_back_edge(
                        f"stall ({verdict})", node, goto,
                        {"stalled": True, "stall_reason": verdict, "repeated_signature": sig,
                         "stall_rounds": len(hist), "stall_window": a.stall_window,
                         "max_revisits": mr},
                        (f"stall detected ({verdict}) on back-edge {node}->{goto}: no verifiable "
                         f"progress over {len(hist)} revisit(s) — STOP, human needed ｜ 原地打轉，交人"))
                used = revisits.get(key, 0)
                if used >= mr:
                    _stop_back_edge(
                        "revisits exhausted", node, goto,
                        {"revisit_exhausted": True, "revisits": used, "max_revisits": mr},
                        (f"back-edge {node}->{goto} exhausted its bound: {mr} revisit(s) used "
                         f"— STOP, human needed ｜ 退回次數已達上限，交人處理"))
                revisits[key] = used + 1
                print(f"  [BACK-EDGE] → {goto}  (revisit {used + 1}/{mr})")
            else:
                print(f"  [BRANCH] → {goto}")
            steps.append({"skill": f"branch→{goto}", "ok": True, "out": art, "error": ""})
            i = target
            continue
        op = resolve(st["out"])
        visits[i] = visits.get(i, 0) + 1
        archived = _archive_previous(op, visits[i])
        ok, err = run_step(st, resolve, inp, a.allow_mutations)
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
        label = st.get("skill") or ("cmd: " + (st.get("cmd", "")[:40] + ("…" if len(st.get("cmd", "")) > 40 else "")))
        steps.append({"skill": label, "ok": ok, "out": op, "error": (err or "")[:600]})
        entry = {"node": node, "visit": visits[i], "kind": "step", "out": op, "ok": ok}
        if archived:
            entry["archived_previous"] = archived
        path_taken.append(entry)
        print(f"  [{'OK' if ok else 'FAIL'}] {label} → {op}"
              + (f"  (visit {visits[i]})" if visits[i] > 1 else ""))
        if not ok:
            _fail(label, err, {"step": label, "gate_type": gate_type,
                               "message": (err or "")[-1000:], "artifact": op})
        last_out = op
        i += 1

    final = last_out
    mani = {"flow": flow["name"], "run_id": rid, "state": "OK_FOR_REVIEW", "steps": steps,
            "final_output": final, "human_review_required": True, "banner": BANNER,
            **_graph_extra()}
    kit.write_artifact(mani, os.path.join(run, "run_manifest.json"))
    print(f"  ✅ 流程完成 → {final}")
    print("  " + BANNER)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
