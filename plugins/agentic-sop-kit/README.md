# agentic-sop-kit — Claude Code plugin

把「人工 SOP」轉成「確定性引擎 + 誠實硬閘門 + 人核准」的 agentic workflow。本 plugin 打包了方法論 skills、`/sop-flow` 指令、**專案範圍**的回歸 Stop-hook，以及可攜的 `agentic-sop-kit`。

## 內容
- **Skills**（model-invoked，安裝後到處可用）
  - `agentic-sop` — 把人工流程工程化成自動代理工作流的方法論與落地入口。
  - `agentic-workflow-audit` — 稽核既有 workflow 是否真拆解，或退化成 mega agent。
- **Command**：`/agentic-sop-kit:sop-flow` — 跑 kit 的 extract→compute→report 編排，回報 DRAFT。
- **Hooks（專案範圍，關鍵設計）**
  - `SessionStart` → 若目前專案有 `agentic-sop-kit/` 就跑 `check_deps.py`，否則略過。
  - `Stop` → 若目前專案有 `agentic-sop-kit/tests/verify.py` 就跑回歸閘門（變更偵測 → 兩層測試 → 失敗以 `decision:block` 餵回去修；重試上限防迴圈），否則略過。
- **`kit/`**：可攜的 `agentic-sop-kit` 副本（含 `bootstrap.py`、`SOP.md`、`lib/`、`workflow/`、`tests/`、`templates/`、範例 skills）。

## 引擎能力（kit 的 `run.py` 編排器，v1.5）
除了線性 demo，引擎還支援以下能力——**全部確定性、由程式決定、附加式**（既有流程照常運作）：
- **每步硬閘門**（產出後驗、fail 即停、零 LLM）：`cmd_gate`（exit 0）／`schema_gate`（必填欄位）／`trace_gate`（值須 verbatim 溯源 → 擋臆造）／`recompute_gate`（數字重算相符）。
- **`cmd` 步驟**（指令只來自 `flow.json` 白名單；會改動環境的需 `--allow-mutations`）＋ **`--plan`** 乾跑（執行前列出所有操作、標示 mutating，不執行）。
- **forward-only 條件分支**（`branch`／`cases`／`goto`）與 **`map_over`**（對清單每項各跑一次、收集）——控制流由程式決定，不交給模型。
- **跨領域範例**：`kit/workflow/examples/` 的免依賴 FE／BE／DB／AI 流程（各示範一個閘門）。
- **封頂自動修復 fix-loop**：閘門失敗時 `/sop-flow` 自動修復重跑（`run.py --max-fix-retries`，預設 3、程式強制上限），用盡才交人；永不竄改輸出過關（與 Stop-hook 回歸**共用同一上限** `SOPKIT_MAX_FIX_RETRIES`，預設 3——兩層、一個旋鈕）。
詳見 `kit/SOP.md`（方法論）與 `kit/workflow/examples/README.md`。

## 安裝（從 GitHub）
在 Claude Code（含 Claude Desktop 的 **Code 分頁**）執行：
```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install agentic-sop-kit@agentic-sop-to-work
/reload-plugins      # 或重開 session
```
> 也可用完整網址：`/plugin marketplace add https://github.com/s0912758806p/agentic-sop-to-work`

驗證：`/help` 應看到 `/agentic-sop-kit:sop-flow`；兩支 skill 會依描述自動觸發。

## 開啟某專案的「強制力」
Hook 是**專案範圍**的：只有當該專案根目錄有 `agentic-sop-kit/` 時，`Stop` 閘門才會驗證**那個專案的** workflow（否則 no-op，不干擾無關專案）。要讓某專案受閘門保護：
```
python3 "<plugin 安裝路徑>/kit/bootstrap.py" --project /path/to/project
# 或用你機器上的 canonical kit：
python3 ~/.claude/agentic-sop-kit/bootstrap.py --project /path/to/project
```
之後在 Claude Code（含 Desktop Code 分頁）開該專案資料夾，`Stop` 時就會自動跑回歸閘門。

## 鐵則
- 事實只來自輸入，缺標【待補】，絕不臆造。
- 確定性的事用程式；硬閘門必須確定性，LLM 自評只能 advisory 且封頂。
- 產出一律 DRAFT + 人核准；受控／高風險判定永遠人擁有。
- **真正的強制力在 hook/gate（本 plugin 的 `Stop` 閘門），不在散文。**

方法論細節見 `kit/SOP.md`。
