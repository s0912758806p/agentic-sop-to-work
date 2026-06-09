---
name: compute
description: Use to compute summary statistics (count/sum/mean/min/max) from a readings artifact, preserving the upstream source trace. Single tool. Reusable standalone.
---

# Skill B — compute（計算統計）

SOP 流程的第 2 步。讀上游 readings、算統計、透傳來源追溯。

## 綁定的單一工具
- `python3`（標準庫 `statistics`）。**本 skill 只此一個工具。**

## 依賴（完整宣告；缺項明確報錯）
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <readings artifact.json>`
- 輸出：`--out <stats artifact.json>`

## 介面
- **輸入 artifact**：`readings@1`（讀 `data.readings[].value`）。
- **輸出 artifact**：`{"schema":"stats@1","produced_by":"compute","data":{"stats":{count,sum,mean,min,max}},"trace":[...透傳...]}`
- 下游（report）讀 `data.stats` 與 `trace`。

## 執行
`python3 skills/compute/tool.py --in <out/a.json> --out <out/b.json>`

## 獨立重用
`skills/compute/` + `lib/kit.py` 可單獨抽出；只要上游給 `readings@1` artifact 即可運作。
