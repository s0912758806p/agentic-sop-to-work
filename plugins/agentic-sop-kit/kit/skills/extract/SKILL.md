---
name: extract
description: Use to extract numeric readings (key: value lines) from a plain-text input into a structured readings artifact with source-location trace. Single tool. Reusable standalone.
---

# Skill A — extract（抽取讀數）

SOP 流程的第 1 步。把文字輸入中的 `key: number`（或 `key = number`）抽成結構化 readings。

## 綁定的單一工具
- `python3`（標準庫；正規表示式 `re`）。**本 skill 只宣告/使用這一個工具。**

## 依賴（完整宣告；缺項由 `kit.require_deps` 明確報錯，非靜默失敗）
- `python` >= 3.8

## 參數化（無硬編碼專案值）
- 輸入：`--in <text 檔>`（任意路徑，由編排層/呼叫端提供）
- 輸出：`--out <artifact.json>`

## 介面（與上下游 skill 的資料格式）
- **輸入**：純文字（每行 `key: number`）。
- **輸出 artifact**：`{"schema":"readings@1","produced_by":"extract","data":{"readings":[{"key","value"}]},"trace":[{"value","source","locator"}]}`
- 下游（compute）讀 `data.readings`。

## 執行
`python3 skills/extract/tool.py --in <input.txt> --out <out/a.json>`

## 獨立重用
本目錄（`skills/extract/`）+ `lib/kit.py` 可單獨抽出放到別專案；無專案專屬硬編碼，依 `--in/--out` 即可運作。
