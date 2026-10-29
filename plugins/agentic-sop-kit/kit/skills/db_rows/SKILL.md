---
name: db_rows
description: Use as the database example step — emit query rows plus a stated total (`rows@1`) that a recompute_gate re-derives and compares. Stand-in for a real SQL query (psql); the gate is what catches a total that does not add up. Single tool.
---

# Example skill — db_rows（資料庫範例：總數要能重算）

`workflow/examples/db.json` 的唯一一步。stand-in 輸出固定的查詢列與它們的加總；
接上真的查詢時換掉 `run()`，**保留 `recompute_gate`**——報出來的總數由程式重算核對，不信任上游自報。

## 綁定的單一工具
- `python3`（標準庫）。實務上換成 `psql` 或 DB driver，一步仍只綁一個工具。

## 依賴（完整宣告；缺項明確報錯）
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <任意輸入>`（stand-in 不讀；真的實作讀查詢參數）
- 輸出：`--out <rows artifact.json>`

## 介面
- **輸出 artifact**：`{"schema":"rows@1","produced_by":"db_rows","data":{"rows":[10,20,30],"total":60},"trace":[]}`
- 閘門：`recompute_gate`，`args = {"op":"sum","over":"rows","equals":"total"}`。

## 執行
`python3 skills/db_rows/tool.py --in <任意輸入> --out <out/db.json>`
