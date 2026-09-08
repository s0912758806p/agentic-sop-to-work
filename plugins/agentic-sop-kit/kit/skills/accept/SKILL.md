---
name: accept
description: Use as a terminal node that emits accepted@1 only when an upstream verdict@1 says pass, and fails loudly on a rejected draft regardless of how routing reached it. Single tool. Reusable standalone.
---

# Skill — accept（終端節點，不信任路由）

圖示範流程的終端節點。刻意**不信任路由**：即使編排把一份 `reject` 的判定送到這裡
（例如有人手改了 `flow.json` 的 branch 條件），這一步仍拒絕通過。
閘門查真相，不查「我是被誰叫來的」。

## 綁定的單一工具
- `python3`（標準庫）。**本 skill 只此一個工具。**

## 依賴
- `python` >= 3.8

## 參數化（無硬編碼）
- 輸入：`--in <verdict artifact.json>`；輸出：`--out <accepted artifact.json>`

## 介面
- **輸入 artifact**：`verdict@1`（讀 `data.verdict`、`data.round`）。
- **輸出 artifact**：`accepted@1` — `data{accepted, rounds, draft_status:"DRAFT"}`，透傳 `trace`。

## fail-loud 邊界
`data.verdict != "pass"` → **exit 3**。產出一律 DRAFT，需人覆核。

## 執行
`python3 skills/accept/tool.py --in <$RUN/verdict.json> --out <$RUN/accepted.json>`

## 獨立重用
`skills/accept/` + `lib/kit.py` 可單獨抽出；只要上游給 `verdict@1` 即可運作。
