---
name: agentic-sop
description: Use when turning a human SOP or manual process into an agentic workflow, building or adding an agent tool, or starting a new agent-workflow project — even if the user never says 'SOP' or 'methodology'. ｜ 要把人工流程／SOP 自動化、建立或新增 agent 工具、或開一個新的 agent 工作流專案時使用；只要意圖是把流程工程化成自動代理就觸發。不適用：稽核既有工作流是否退化成 mega agent（改用 agentic-workflow-audit）。
---

# Agentic SOP — 把人工流程做成可治理的 agent 工作流

## 何時用 / 不用
- **用**：要把人工 SOP／手動流程自動化、建新 agent 工具、設計「拆解＋閘門」、或開新的 agent 工作流專案時。任何專案皆適用，尤其未來新項目。
- **不用**：稽核既有工作流是否退化成 mega agent → 用 `agentic-workflow-audit`；執行既有 GMP 產生器 → 用該工具自己的 skill。

## 開場：先判斷輸入型態（intake 分流）
觸發後**第一件事**——看使用者怎麼來，別急著動工：
- **已有正式輸入**（寫好的 spec／既有 requirement 或 runner skill／已填好的 `templates/human_sop_template.md`）→ **照原樣採用**、不重寫，直接進下面的拆解。
- **只有自然語言需求/任務** → 先用 `templates/human_sop_template.md` **起草一份 Human SOP**：能由輸入得到的填上、未知的標【待補】（**絕不臆造**）；草稿好 **STOP 給人看一眼**（「這樣有抓到你的流程嗎？改／確認」）→ 確認後才續入拆解。
- **判不準** → 問一個澄清問題，別猜路。
草稿 SOP 也是 **DRAFT**（受「DRAFT＋人核准」約束）；本步只動生成層，**不碰引擎/閘門**。

## 核心模型（三段鏈，缺一不可）
Human SOP → **工具 Skill（SKILL.md）** → Agentic Workflow（編排 + 誠實閘門 + hook）。
中間的 Skill 環最易被忘：**工具一改，SKILL.md 必須同次更新**。每支工具實作同一條七階段迴圈：
intake → 分類/前置檢查 → 確定性層(程式) → 生成層(Claude，只整理輸入) → 組裝 DRAFT → 閘門自評(≤2 次) → 覆核包 → 人核准 STOP。

## 落地：導入 agentic-sop-kit（不要重造）
方法論已封裝成可攜套件，**直接導入、別重寫**：
1. 一鍵導入：`python3 ~/.claude/agentic-sop-kit/bootstrap.py --project /path/to/project`（複製 kit＋裝 `/sop-flow`＋合併 Stop-hook）。canonical 在 `~/.claude/agentic-sop-kit/`。
2. `python3 agentic-sop-kit/check_deps.py` 驗依賴；`workflow/run.py` 跑通範例。
3. 用 `templates/human_sop_template.md` 寫 SOP（每步標工具）；依拆解規則把每個「步驟×工具」用 `templates/skill_template/` 建成 `skills/<name>/`。
4. 在 `workflow/flow.json` 按 SOP 順序接線；裝 `commands/` + `hooks/`。
詳見 kit 的 `SOP.md`（方法論 canonical）與 `README.md`（安裝）。

## 跨專案鐵則（為什麼）
- **事實只來自輸入**，缺標【待補】，絕不臆造編號/日期/姓名/結論——臆造會在下游被當成事實，汙染整條鏈。
- **確定性的事用程式、不用 LLM**；硬閘門必須確定性、hermetic；LLM 自評一律 advisory 且封頂於確定性——否則模型替自己放水（弱閘門＝假自主）。
- **DRAFT + 人核准 STOP**；受控/高風險判定永遠人擁有。
- **閘門查真相、不查形式**：別用 token 重疊/關鍵字出現/grep 編號當硬閘門（可被字詞游戲化），要對權威來源核對。

## 「保證遵守」來自 hook，不是這支 skill
本 skill 是**提醒與指引**（散文，機率性）。真正的強制力在 kit 的 **Stop-hook 自動回歸**：更新後有變動才跑「受影響單元＋整合」兩層，fail 就 `decision:block` 把原因餵回去修，附重試上限防迴圈。要讓某專案「真的被擋」，就把 kit 的 `hooks/`（SessionStart 依賴檢查 + Stop 回歸）裝上。
