---
name: verdict
description: Use to derive a deterministic reject/pass verdict from a draft@1 artifact's open-defect count, emitting a verdict@1 artifact for a branch to route on. Single tool. Reusable standalone.
---

# Skill — verdict（判定，退回邊的判定來源）

圖示範流程的第 2 步。判定**完全確定性**：由上游 `defects` 導出，不由模型決定；
編排層再用 branch predicate 讀 `data.verdict` 決定往前或走退回邊——控制流始終在程式裡。

## 綁定的單一工具
- `python3`（標準庫）。**本 skill 只此一個工具。**

## 依賴
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <draft artifact.json>`；輸出：`--out <verdict artifact.json>`

## 介面
- **輸入 artifact**：`draft@1`（讀 `data.defects`、`data.round`）。
- **輸出 artifact**：`verdict@1` — `data{verdict: "reject"|"pass", defects, round}`，透傳 `trace`。

## fail-loud 邊界
上游沒有 `defects` 欄位 → **exit 3**，不臆測判定（缺資料不得猜結論）。

## 執行
`python3 skills/verdict/tool.py --in <$RUN/draft.json> --out <$RUN/verdict.json>`

## 獨立重用
`skills/verdict/` + `lib/kit.py` 可單獨抽出；只要上游給 `draft@1` 即可運作。
