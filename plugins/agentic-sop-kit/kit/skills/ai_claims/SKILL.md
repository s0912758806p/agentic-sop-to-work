---
name: ai_claims
description: Use as the AI/LLM example step — turn an input's `source` values into `claims`, recording a trace entry per value so a trace_gate can block anything not traceable to the input (the no-fabrication pattern). Stand-in for a real LLM call. Single tool.
---

# Example skill — ai_claims（AI 範例：每個值都可溯源）

`workflow/examples/ai.json` 的唯一一步。示範「模型產出的每個值都要能溯回輸入」：
本 stand-in 只把輸入的 `source` 原樣抄成 `claims`，並為每個值記一筆 trace。

## 綁定的單一工具
- `python3`（標準庫）。換成真的 LLM 呼叫時，**保留下游的 `trace_gate`**——模型自己發明、輸入裡找不到的值會被擋下。

## 依賴（完整宣告；缺項明確報錯）
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <artifact.json>`（讀 `data.source`，一個清單）
- 輸出：`--out <claims artifact.json>`

## 介面
- **輸出 artifact**：`{"schema":"claims@1","produced_by":"ai_claims","data":{"claims":[...]},"trace":[{"value":"<str>","source":"<輸入檔名>","locator":"source[i]"}]}`
- 閘門：`trace_gate`，`args.fields = "claims"`。

## 執行
`python3 skills/ai_claims/tool.py --in example/inputs/ai_source.json --out <out/ai.json>`
