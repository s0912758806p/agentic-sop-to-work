# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Demo skill：draft — 產出（或依審查意見修訂）一份草稿，輸出 draft@1。

圖示範流程的第 1 步，也是**有界退回邊的目標節點**。刻意保持無狀態：
第一次沒有上游 verdict（檔案不存在）→ 開新草稿；被退回時 `--in` 就是上一輪的
`verdict@1` → 依其 `defects` 修掉一項再送審。所以「這是第幾輪」由 artifact 本身
攜帶，不靠任何隱含計數器——重跑同一份輸入永遠得到同一結果。

單一工具（python3 stdlib）；路徑由 --in/--out 參數化。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "draft"
OPEN_DEFECTS = 2          # a fresh draft starts with this many known gaps


def run(inp, out):
    prior = None
    if os.path.exists(inp):
        try:
            up = kit.read_artifact(inp)
            if up.get("schema") == "verdict@1":
                prior = up.get("data") or {}
            # Any other upstream artifact is the raw input for a first draft, not feedback.
        except ValueError:
            prior = None                      # not JSON -> a plain input file, first draft
    if prior is None:
        data = {"defects": OPEN_DEFECTS, "round": 1, "addressed": []}
    else:
        remaining = max(0, int(prior.get("defects", OPEN_DEFECTS)) - 1)
        rnd = int(prior.get("round", 1)) + 1
        data = {"defects": remaining, "round": rnd,
                "addressed": [f"defect fixed in round {rnd}"]}
    kit.write_artifact(kit.artifact("draft@1", WHO, data), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
