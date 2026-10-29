#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Stop hook（專案版，相容 shim）：Claude 每次「準備停止」時，自動跑本 kit 的回歸驗證（tests/verify.py）。

行為全在 `_regression_core.stop_gate`（與 plugin 的 hooks/stop_gate.py 共用同一份實作）：
變更偵測 → 失敗以 {"decision":"block"} 餵回去修 → stop_hook_active + 重試上限
（SOPKIT_MAX_FIX_RETRIES，預設 3）防無限迴圈。

v1.10.1 起 bootstrap.py 預設**不再**把本 hook 寫進專案 settings（改由 plugin hook 負責）。
本檔保留給 v1.10.0 以前導入、settings 仍註冊它的專案，以及沒裝 plugin、以
`bootstrap.py --with-hooks` 手動安裝的人。兩者並存時 plugin hook 會自動讓位，不會雙跑。
"""
import os
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOK_DIR)
from _regression_core import stop_gate  # noqa: E402

if __name__ == "__main__":
    sys.exit(stop_gate(os.path.dirname(HOOK_DIR),
                       log_display=os.path.join("agentic-sop-kit", "tests", "regression_log.jsonl")))
