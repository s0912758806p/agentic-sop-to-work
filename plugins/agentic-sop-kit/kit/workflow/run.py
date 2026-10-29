# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Agentic Workflow 編排層：依 flow.json 的順序串接各 skill；run-scoped manifest；人核准 STOP。
本檔只剩 argparse ＋ 分派；執行迴圈在 sopkit/runner.py（RunContext / build_manifest / step_loop），
步驟執行器在 sopkit/engine.py。退出碼：0 = 完成（DRAFT）；2 = 失敗。

失敗時 manifest 帶機器可讀 `failure{step,gate_type,message,artifact}`，供上層定向修復。
`--max-fix-retries N`（預設讀 `SOPKIT_MAX_FIX_RETRIES`、否則 3；與 Stop-hook 回歸共用同一上限）對同一 `--run-id` 封頂自動修復重試：這支引擎只負責**程式強制的上限**
——同一 run-id **失敗**超過 1+N 次即拒跑、寫 `fix_exhausted`（成功的執行不消耗額度）；實際的修復（重生/改輸入）由 `/sop-flow`
的 Claude 層執行，引擎本身維持零 LLM、確定性。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # kit root → sopkit
from sopkit import config, graph, kit, runner  # noqa: E402
from sopkit.console import safe_print  # noqa: E402
from sopkit.engine import print_plan  # noqa: E402

FLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow.json")
BANNER = runner.BANNER


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
    ap.add_argument("--max-fix-retries", type=int, default=config.max_fix_retries(),
                    help="code-enforced ceiling on auto-fix re-runs per --run-id (default: $SOPKIT_MAX_FIX_RETRIES or 3, shared with the Stop-hook regression loop); "
                         "the fixing itself is done by the /sop-flow Claude layer, not here")
    ap.add_argument("--stall-window", type=int, default=config.stall_window(),
                    help="stall early-stop: how many consecutive identical failure signatures count as "
                         "'no progress' (default: $SOPKIT_STALL_WINDOW or 2; 0 disables; cycle cap fixed at 2). "
                         "Deterministic, zero-LLM — complements the budget ceiling.")
    ap.add_argument("--prune", action="store_true",
                    help="evict run dirs beyond SOPKIT_STATE_KEEP_RUNS (newest kept); deletes — human-authorized")
    a = ap.parse_args(argv)

    base, notice = config.runs_base(a.out_base)
    if notice and not (a.graph or a.plan):
        safe_print("  ⚠️ " + notice, file=sys.stderr)
    if a.prune:
        raise SystemExit(runner.prune_runs(base, config.keep_runs()))

    with open(a.flow, encoding="utf-8") as f:
        flow = json.load(f)

    if a.graph:
        safe_print(graph.mermaid(flow))
        raise SystemExit(0)

    n, keep = runner.count_run_dirs(base), config.keep_runs()
    if n > keep:
        safe_print(f"  ℹ️ {n} run-dirs (keep {keep}); {n - keep} prunable — run with --prune ｜ 可清舊 run")

    if a.plan:
        raise SystemExit(print_plan(flow, a.stall_window))

    ctx = runner.RunContext(flow, kit.run_dir(base, a.run_id),
                            a.input or kit.kit_path(flow["input_default"]),
                            max_fix_retries=a.max_fix_retries, stall_window=a.stall_window,
                            allow_mutations=a.allow_mutations)
    runner.preflight(ctx)
    runner.step_loop(ctx)


if __name__ == "__main__":
    main()
