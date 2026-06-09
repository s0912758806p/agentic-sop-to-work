#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Stop hook：Claude 每次「準備停止」時，自動跑回歸驗證（tests/verify.py）。

行為（對應任務 2）：
  • verify.py 內含變更偵測——SOP/任一 skill/編排層自上次通過後無變動 → 直接放行（不跑測試）。
  • 全部 pass（或無變更）→ 放行停止（exit 0），重試計數歸零。
  • 任一 fail → 以 {"decision":"block","reason":...} 把失敗詳情餵回 Claude 去修；保留回歸紀錄供人決定修正/回滾。
  • 防迴圈：用 Stop hook 輸入的 stop_hook_active 旗標 + 持久重試計數設上限（預設 3，可用 SOPKIT_MAX_FIX_RETRIES 覆寫）。
    達上限即停止再 block（放行停止）、改以明顯訊息要求人工介入，避免「失敗→修→再觸發→再失敗」無限循環。
  • 「更好」指標（步數/時間/成功率）只由 verify 記入 log，本 hook 不據此下結論。

安裝：把本 kit 的 hooks 區段合併進目標專案 .claude/settings.json（見 hooks/settings.snippet.json）。
"""
import json
import os
import subprocess
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HOOK_DIR)
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

    # kit 不存在/無 verify → 無回歸可跑，放行（不干擾無關專案的停止）。
    if not os.path.exists(VERIFY):
        return 0

    r = subprocess.run([sys.executable, VERIFY], cwd=KIT, capture_output=True, text=True)
    out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")

    if r.returncode == 0:
        _write_count(0)            # 通過或無變更 → 重置防迴圈計數，放行停止
        return 0

    # 失敗（exit 2 測試失敗 / exit 3 登錄表錯誤）。
    # 防迴圈：非 hook 續跑造成的停止（stop_active=False）視為全新一輪 → 計數歸零後再評估。
    count = _read_count() if stop_active else 0
    if stop_active and count >= MAX_RETRIES:
        _write_count(0)
        sys.stderr.write(
            f"\n⚠️ 回歸測試連續失敗已達重試上限（{MAX_RETRIES}）。停止自動修復迴圈，請人工介入（修正或回滾）。\n"
            f"回歸紀錄：{os.path.join('agentic-sop-kit', 'tests', 'regression_log.jsonl')}\n"
            f"最後結果摘要：\n{out[-1500:]}\n")
        return 0                   # 放行停止，交人處理（不再 block，避免無限循環）

    _write_count(count + 1)
    reason = (
        f"自動回歸驗證未通過（嘗試 {count + 1}/{MAX_RETRIES}）。"
        f"請依下列失敗詳情修正受影響的 skill / workflow；修好後我會在你再次停止時自動重跑回歸測試。"
        f"若判斷應回滾而非修正，請明說並停手交人決定。\n\n{out[-6000:]}")
    _emit({"decision": "block", "reason": reason})
    return 0


if __name__ == "__main__":
    sys.exit(main())
