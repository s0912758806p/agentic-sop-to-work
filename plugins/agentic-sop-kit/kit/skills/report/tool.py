# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Skill C 工具：report — 讀 stats artifact，輸出 Markdown DRAFT 報告（含來源追溯區），標 DRAFT、需人覆核。
單一工具（python3 stdlib）。輸出為 .md（非 JSON）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "report"


def run(inp, out):
    up = kit.read_artifact(inp)
    s = up["data"]["stats"]
    lines = [
        "# Measurement Summary — DRAFT", "",
        "> DRAFT — 需人員覆核；由 agentic-sop-kit 範例流程產生，非正式紀錄。", "",
        "## Summary",
        f"- count: {s['count']}", f"- sum: {s['sum']}", f"- mean: {s['mean']}",
        f"- min: {s['min']}", f"- max: {s['max']}", "",
        "## 來源追溯（每個讀數溯回輸入位置）",
    ]
    for t in up.get("trace", []):
        lines.append(f"- {t.get('value')} @ {t.get('source')}:{t.get('locator')}")
    skipped = up["data"].get("skipped", [])
    if skipped:
        lines += ["", f"## ⚠️ 未解析行（{len(skipped)} 行，已跳過，需人工確認）"]
        for x in skipped:
            lines.append(f"- line {x.get('line')}: {x.get('text')}")
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    kit.skill_main(DEPS, WHO, run)
