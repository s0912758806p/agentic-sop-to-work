---
name: report
description: Use to render a DRAFT Markdown summary report from a stats artifact, including a source-trace section; output is always a DRAFT for human review. Single tool. Reusable standalone.
---

# Skill C — report（產出 DRAFT 報告）

SOP 流程的第 3 步。讀上游 stats，輸出標示 DRAFT 的 Markdown 報告（含來源追溯區）。

## 綁定的單一工具
- `python3`（標準庫）。**本 skill 只此一個工具。**

## 依賴（完整宣告；缺項明確報錯）
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <stats artifact.json>`
- 輸出：`--out <report.md>`

## 介面
- **輸入 artifact**：`stats@1`（讀 `data.stats` 與 `trace`）。
- **輸出**：Markdown `.md`，開頭標 **DRAFT — 需人員覆核**；附來源追溯區。

## 執行
`python3 skills/report/tool.py --in <out/b.json> --out <out/report.md>`

## 獨立重用
`skills/report/` + `lib/kit.py` 可單獨抽出；只要上游給 `stats@1` artifact 即可運作。產出永遠是 DRAFT，永不自動歸檔。
