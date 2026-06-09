---
name: agentic-sop
description: 把人工流程／Human SOP 轉成「確定性引擎 + 誠實硬閘門 + 人核准」的 agentic workflow 時的方法論與落地入口——適用任何專案、尤其未來新開發項目。當使用者要把一份人工 SOP／手動流程自動化、建立或新增 agent 工具、設計 SOP→Skill→Workflow 的拆解與閘門、或開一個新的 agent 工作流專案時，主動套用本技能：它給三階段拆解規則、七階段迴圈、跨專案鐵則（不臆造／DRAFT＋人核准／確定性用程式／硬閘門確定性），並指示導入可攜的 agentic-sop-kit（含自動回歸 Stop-hook＝真正的強制層）。即使沒講「方法論」或「SOP」，只要意圖是把流程工程化成自動代理工作流就應觸發。不適用：稽核／檢視既有工作流是否退化成 mega agent（改用 agentic-workflow-audit）；直接執行既有 GMP 產生器（cr-form-gen／lir-mir-draft／template-doc-gen）。
---

# Agentic SOP — 把人工流程做成可治理的 agent 工作流

## 何時用 / 不用
- **用**：要把人工 SOP／手動流程自動化、建新 agent 工具、設計「拆解＋閘門」、或開新的 agent 工作流專案時。任何專案皆適用，尤其未來新項目。
- **不用**：稽核既有工作流是否退化成 mega agent → 用 `agentic-workflow-audit`；執行既有 GMP 產生器 → 用該工具自己的 skill。

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
