---
name: be_api
description: Use as the backend example step — emit an API-response artifact (`api@1`) that a schema_gate checks for required fields. Stand-in for a real HTTP call (curl / requests); the gate is what catches a malformed response. Single tool.
---

# Example skill — be_api（後端範例：回應要過 schema 閘門）

`workflow/examples/be.json` 的唯一一步。stand-in 輸出一筆固定的「API 回應」；
真正接上 API 時換掉 `run()`，**保留 `schema_gate`**，缺欄位的回應就不會流到下游。

## 綁定的單一工具
- `python3`（標準庫）。實務上換成 `curl` 或 HTTP client，一步仍只綁一個工具。

## 依賴（完整宣告；缺項明確報錯）
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <任意輸入>`（stand-in 不讀；真的實作讀請求參數）
- 輸出：`--out <api artifact.json>`

## 介面
- **輸出 artifact**：`{"schema":"api@1","produced_by":"be_api","data":{"id":1,"name":"widget","price":9.99},"trace":[]}`
- 閘門：`schema_gate`，`args.required = ["id","name"]`。

## 執行
`python3 skills/be_api/tool.py --in <任意輸入> --out <out/be.json>`
