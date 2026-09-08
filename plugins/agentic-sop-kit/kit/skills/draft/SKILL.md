---
name: draft
description: Use to produce a first draft, or to revise one from an upstream verdict artifact's open-defect count, emitting a draft@1 artifact. The target node of a bounded back-edge. Single tool. Reusable standalone.
---

# Skill — draft（起草／依審查意見修訂）

圖示範流程（`workflow/examples/graph.json`）的第 1 步，也是**有界退回邊的目標節點**。

## 綁定的單一工具
- `python3`（標準庫）。**本 skill 只此一個工具。**

## 依賴（完整宣告；缺項由 kit.require_deps 明確報錯，非靜默）
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <verdict artifact.json ／ 不存在皆可>`
- 輸出：`--out <draft artifact.json>`

## 介面
- **輸入 artifact**：`verdict@1`（讀 `data.defects` 與 `data.round`）。
  **輸入不存在或不是 `verdict@1` → 視為初稿**（第一次進入節點時 `$RUN/verdict.json` 還沒產生）。
- **輸出 artifact**：`draft@1` — `data{defects, round, addressed[]}`。

## 為何無狀態
「這是第幾輪」由上游 artifact 攜帶，不靠隱含計數器：同一份輸入重跑永遠得到同一結果
（確定性），而重訪之所以會前進，是因為上一輪的 verdict 真的被讀進來了。

## 執行
`python3 skills/draft/tool.py --in <$RUN/verdict.json> --out <$RUN/draft.json>`

## 獨立重用
`skills/draft/` + `lib/kit.py` 可單獨抽出；只要給得出 `verdict@1`（或不給）即可運作。
