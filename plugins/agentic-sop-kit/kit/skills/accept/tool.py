# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Demo skill：accept — 讀 verdict@1，只有 pass 才輸出 accepted@1，否則 fail-loud。

圖示範流程的終端節點。刻意**不信任路由**：即使編排把一份 reject 的判定送到這裡
（例如有人手改了 flow.json 的 branch 條件），這一步仍拒絕通過——閘門查真相，
不查「我是被誰叫來的」。輸出一律 DRAFT，需人覆核。

單一工具（python3 stdlib）。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "accept"


def run(inp, out):
    up = kit.read_artifact(inp)
    d = up.get("data") or {}
    if d.get("verdict") != "pass":
        print(f"ERROR: [{WHO}] verdict is {d.get('verdict')!r}, not 'pass' — refusing to accept a "
              f"rejected draft ｜ 未通過的草稿不得放行", file=sys.stderr)
        raise SystemExit(3)
    rounds = int(d.get("round", 1))
    data = {"accepted": True, "rounds": rounds, "draft_status": "DRAFT"}
    # A derived number still needs provenance: name the upstream artifact and field it came
    # from, so a downstream honesty check can trace it instead of flagging it as invented.
    trace = list(up.get("trace", [])) + [
        {"value": str(rounds), "source": up.get("schema", "verdict@1"), "locator": "data.round"}]
    kit.write_artifact(kit.artifact("accepted@1", WHO, data, trace), out)


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
