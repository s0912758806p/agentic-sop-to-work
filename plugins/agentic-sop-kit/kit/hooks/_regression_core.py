# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Shared logic of the kit's Stop / SessionStart hooks — the ONE implementation.

Two entry points call it:
  • the plugin hooks (<plugin>/hooks/stop_gate.py, session_check.py) — the default since
    v1.10.1: bootstrap.py no longer writes hooks into a project;
  • the project hook kit/hooks/stop_regression.py — kept as a shim for projects bootstrapped
    before v1.10.1, whose .claude/settings.json still registers it.

When both are present the plugin hook steps aside (`project_registers`), so verify.py runs
once per stop and tests/.retry_count is not shared by two gates (which halved the cap).

Stop gate behaviour:
  • verify.py has change-detection — no relevant change since the last pass → pass-through.
  • all pass (or no change) → allow stop (exit 0) and reset the retry counter.
  • any fail → emit {"decision":"block","reason":...} feeding the failure detail back to
    Claude to fix; the regression log is kept for a human decide-fix-or-rollback.
  • loop guard: the `stop_hook_active` flag + a persistent retry counter capped at
    SOPKIT_MAX_FIX_RETRIES (default 3). At the cap, stop blocking and ask for a human.
Blocking is signalled via stdout JSON, not the exit code; the Stop gate always exits 0.

Pure stdlib; never imports the kit's lib/ (a hook must work even if lib/ is broken).
"""
import json
import os
import subprocess
import sys

STOP_MARK = "stop_regression.py"
SESSION_MARK = "check_deps.py"


def project_registers(project, event, mark):
    """True when the project's own settings already run `mark` on `event`.

    Only settings.json / settings.local.json are read. An unreadable file counts as "not
    registered": a broken settings file must never silently disable the plugin's gate.
    """
    for name in ("settings.json", "settings.local.json"):
        path = os.path.join(project, ".claude", name)
        try:
            with open(path, encoding="utf-8") as f:
                hooks = (json.load(f) or {}).get("hooks") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for entry in hooks.get(event) or []:
            for h in (entry or {}).get("hooks") or []:
                cmd = h.get("command") or ""
                args = h.get("args") or []
                if mark in cmd or any(mark in str(a) for a in args):
                    return True
    return False


def _read_count(path):
    try:
        with open(path, encoding="utf-8") as f:
            return int((f.read().strip() or "0"))
    except Exception:
        return 0


def _write_count(path, n):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(n))
    except OSError:
        pass


def _stop_active(stdin):
    raw = ""
    try:
        if not stdin.isatty():
            raw = stdin.read()
    except Exception:
        raw = ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}
    return bool(data.get("stop_hook_active", False))


def stop_gate(kit, log_display=None, stdin=None):
    """Run <kit>/tests/verify.py and turn a failure into a Stop-hook block. Returns 0."""
    stop_active = _stop_active(stdin or sys.stdin)
    verify = os.path.join(kit, "tests", "verify.py")
    count_file = os.path.join(kit, "tests", ".retry_count")
    max_retries = int(os.environ.get("SOPKIT_MAX_FIX_RETRIES", "3"))

    # The kit is absent / has no verify → nothing to enforce, allow stop.
    if not os.path.exists(verify):
        return 0

    r = subprocess.run([sys.executable, verify], cwd=kit, capture_output=True, text=True)
    out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")

    if r.returncode == 0:
        _write_count(count_file, 0)        # passed or no change → reset loop counter, allow stop
        return 0

    # Failure (verify exit 2 = test fail / exit 3 = registry error).
    # Loop guard: a stop NOT caused by a prior hook-continue (stop_active=False) is a fresh
    # round → reset the counter before evaluating.
    count = _read_count(count_file) if stop_active else 0
    if stop_active and count >= max_retries:
        _write_count(count_file, 0)
        log = log_display or os.path.join(kit, "tests", "regression_log.jsonl")
        sys.stderr.write(
            f"\n⚠️ 回歸測試連續失敗已達重試上限（{max_retries}）。停止自動修復迴圈，請人工介入（修正或回滾）。\n"
            f"回歸紀錄：{log}\n"
            f"最後結果摘要：\n{out[-1500:]}\n")
        return 0                           # allow stop, hand to a human (avoid an infinite loop)

    _write_count(count_file, count + 1)
    reason = (
        f"自動回歸驗證未通過（嘗試 {count + 1}/{max_retries}）。"
        f"請依下列失敗詳情修正受影響的 skill / workflow；修好後我會在你再次停止時自動重跑回歸測試。"
        f"若判斷應回滾而非修正，請明說並停手交人決定。\n\n{out[-6000:]}")
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


def session_check(kit):
    """Run <kit>/check_deps.py so missing dependencies fail loud at session start."""
    check = os.path.join(kit, SESSION_MARK)
    if not os.path.exists(check):
        return 0
    return subprocess.run([sys.executable, check]).returncode
