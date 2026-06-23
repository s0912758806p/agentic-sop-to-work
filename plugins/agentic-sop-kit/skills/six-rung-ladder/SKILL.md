---
name: six-rung-ladder
description: Use when deciding whether to write a piece of code, add a dependency, or introduce an abstraction / module / config — the "should I build this at all?" filter, applied before building. ｜ 要決定「要不要寫這段 code／引這個依賴／加這層抽象或模組」時使用——「到底該不該做」的過濾網，動手之前先走一遍。不適用：把流程做成 agent workflow／建工具（改用 agentic-sop）；稽核既有架構有沒有拆好（改用 agentic-workflow-audit）。
---

# 極簡架構過濾網：Six-Rung Ladder

## 角色與目標
面對任何「要不要寫這段代碼／要不要引入這個東西」的決策時，當一道**逐級過濾網**。核心信念：**Lazy, not negligent（慵懶，但絕不疏漏）**。每一行代碼、每一個依賴、每一個抽象，都是未來的維護成本與攻擊面；最便宜、最安全的代碼，是那行你沒有寫的。

這把梯子是 **decide → build → audit** 方法論的**最前段**：先用它擋掉不該做的，剩下該做的才交給 `agentic-sop` 去建、`agentic-workflow-audit` 去查。

## 怎麼用
請求從第 1 級開始往下走，**能在哪一級攔下，就在哪一級解決，絕不下沉**。一旦某級給出可行解就停，不要繼續往下找更重的方案。

### 1. YAGNI — 業務真的需要嗎？
不需要 → **直接拒絕**。先質疑需求本身，而不是急著找實現方案。

### 2. Stdlib — 標準庫能解決嗎？
優先用語言／執行環境的原生標準庫：大規模驗證、零供應鏈風險、零安裝、隨語言一起維護。
> **這一級在本專案是機械化的，不是口號**：engine 純標準庫由 `kit/tests/test_no_third_party.py` 守（回歸時 fail-loud），整個 marketplace 的 stdlib-only 不變量由 `plugin-forge lint --all --strict` 守。

### 3. Native Platform — 平台原生特性夠用嗎？
引入任何函式庫之前，先確認平台是否已提供（瀏覽器 `fetch` / `URL` / `Intl`、CSS 原生特性……往往足以取代一整包依賴）。

### 4. Installed Dependency — 現有依賴能複用嗎？
前三級都不行，先翻一遍已經裝好的依賴。**堅決不為了一個小功能引入新的供應鏈風險**——每個新依賴都是新的版本維護、安全漏洞與授權問題來源。
> 同第 2 級：新依賴會被 `test_no_third_party` / `plugin-forge lint` 擋下——這一級有 gate，不靠自律。

### 5. One Line — 一行乾淨代碼行不行？
與其引入抽象、新模組或新依賴，不如就地寫一行清晰直白的代碼。前提：乾淨、可讀、意圖明確，而非炫技式壓縮。

### 6. The Minimum That Works — 最小可用閉環
全走不通 → 只寫最小可用、能跑能驗的閉環。不過度設計、不預留花俏擴展點；先讓最小版本真正運作起來。

## 死守紅線：Lazy, not negligent
「慵懶」是對複雜度／抽象／依賴**保持吝嗇**；「絕不疏漏」是**有些東西一行都不准省**。下列防禦性代碼**永遠不適用上面的偷懶哲學**：

- **跨信任邊界的防注入**：任何外部資料（用戶輸入、第三方回應、檔案內容、URL 參數……）一律當作不可信，做好校驗與轉義。
- **容災與錯誤處理**：失敗路徑、超時、重試、降級，該寫的都要寫，不能假設一切正常。
- **安全性**：權限校驗、機密處理、最小權限原則，不能因「先跑起來再說」而跳過。

> 這條紅線與本專案既有鐵則「**防禦代碼不准省**」是同一條；對應的確定性 gate（如 `trace_gate` 防臆造）亦屬此列。在該懶的地方懶到極致，在該嚴的地方一步不讓。

## 速查口訣
| 級別 | 名稱 | 一句話 |
|---|---|---|
| 1 | YAGNI | 業務真需要嗎？不需要就拒絕。 |
| 2 | Stdlib | 標準庫能不能搞定？（有 gate） |
| 3 | Native Platform | 平台原生特性夠不夠用？ |
| 4 | Installed Dependency | 現有依賴能不能複用？（有 gate） |
| 5 | One Line | 一行乾淨代碼行不行？ |
| 6 | Minimum That Works | 都不行就寫最小可用閉環。 |

**紅線**：防注入、容災、安全性 — 防禦代碼不准省略。

## 輸出格式
被觸發時，對該決策逐級回報：**在第幾級攔下、為什麼、具體方案**（或：為何必須下沉到下一級）。若涉及外部輸入／失敗路徑／安全，明確點出哪條紅線項不得偷懶。最後一句結論：**做 ／ 不做 ／ 做最小版**。
