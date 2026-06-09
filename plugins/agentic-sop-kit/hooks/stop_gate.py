#!/usr/bin/env python3
"""Plugin Stop hook — PROJECT-SCOPED regression gate.

Runs the CURRENT project's agentic-sop-kit/tests/verify.py when present, and
NO-OPS otherwise. This keeps enforcement scoped to projects that have actually
adopted the kit (e.g. via bootstrap.py), so installing this plugin globally
never fires regression in unrelated projects.

Behaviour mirrors the kit's own Stop hook (hooks/stop_regression.py):
  • verify.py has change-detection — no relevant change since last pass → pass-through.
  • all pass (or no change) → allow stop (exit 0), reset the retry counter.
  • any fail → emit {"decision":"block","reason":...} feeding the failure detail
    back to Claude to fix; the regression log is kept for a human decide-fix-or-rollback.
  • loop guard: the Stop-hook `stop_hook_active` flag + a persistent retry counter
    capped at SOPKIT_MAX_FIX_RETRIES (default 3). At the cap, stop blocking and ask
    for a human, to avoid an infinite fail→fix→retrigger loop.

Blocking is signalled via stdout JSON, not the exit code; this script always exits 0.
"""
import json
import os
import subprocess
import sys

PROJECT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
KIT = os.path.join(PROJECT, "agentic-sop-kit")
VERIFY = os.path.join(KIT, "tests", "verify.py")
COUNT_FILE = os.path.join(KIT, "tests", ".retry_count")
MAX_RETRIES = int(os.environ.get("SOPKIT_MAX_FIX_RETRIES", "3"))


def _read_count():
    try:
        with open(COUNT_FILE, encoding="utf-8") as f:
            return int((f.read().strip() or "0"))
    except Exception:
        return 0


def _write_count(n):
    try:
        with open(COUNT_FILE, "w", encoding="utf-8") as f:
            f.write(str(n))
    except OSError:
        pass


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


def main():
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except Exception:
        raw = ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}
    stop_active = bool(data.get("stop_hook_active", False))

    # This project has not adopted the kit → nothing to enforce, allow stop.
    if not os.path.exists(VERIFY):
        return 0

    r = subprocess.run([sys.executable, VERIFY], cwd=KIT, capture_output=True, text=True)
    out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")

    if r.returncode == 0:
        _write_count(0)            # passed or no change → reset loop counter, allow stop
        return 0

    # Failure (verify exit 2 = test fail / exit 3 = registry error).
    # Loop guard: a stop NOT caused by a prior hook-continue (stop_active=False) is a
    # fresh round → reset the counter before evaluating.
    count = _read_count() if stop_active else 0
    if stop_active and count >= MAX_RETRIES:
        _write_count(0)
        sys.stderr.write(
            f"\n⚠️ 回歸測試連續失敗已達重試上限（{MAX_RETRIES}）。停止自動修復迴圈，請人工介入（修正或回滾）。\n"
            f"回歸紀錄：{os.path.join(KIT, 'tests', 'regression_log.jsonl')}\n"
            f"最後結果摘要：\n{out[-1500:]}\n")
        return 0                   # allow stop, hand to a human (no longer block, avoid infinite loop)

    _write_count(count + 1)
    reason = (
        f"自動回歸驗證未通過（嘗試 {count + 1}/{MAX_RETRIES}）。"
        f"請依下列失敗詳情修正受影響的 skill / workflow；修好後我會在你再次停止時自動重跑回歸測試。"
        f"若判斷應回滾而非修正，請明說並停手交人決定。\n\n{out[-6000:]}")
    _emit({"decision": "block", "reason": reason})
    return 0


if __name__ == "__main__":
    sys.exit(main())
