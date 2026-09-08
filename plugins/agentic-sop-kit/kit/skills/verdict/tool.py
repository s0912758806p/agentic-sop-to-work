# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Demo skill：verdict — 讀 draft@1，輸出 verdict@1（reject / pass）。

圖示範流程的第 2 步，也是退回邊的**判定來源**。判定完全確定性：verdict 由上游
artifact 的 `defects` 導出，不由模型決定。編排層再用 branch predicate 讀這個欄位
決定往前走還是走退回邊——控制流始終在程式裡。

單一工具（python3 stdlib）。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "verdict"


def run(inp, out):
    up = kit.read_artifact(inp)
    d = up.get("data") or {}
    if "defects" not in d:
        print(f"ERROR: [{WHO}] upstream draft@1 has no 'defects' field — refusing to guess a "
              f"verdict ｜ 上游缺 defects，不臆測判定", file=sys.stderr)
        raise SystemExit(3)
    defects = int(d["defects"])
    data = {"verdict": ("reject" if defects > 0 else "pass"),
            "defects": defects, "round": int(d.get("round", 1))}
    kit.write_artifact(kit.artifact("verdict@1", WHO, data, up.get("trace", [])), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
