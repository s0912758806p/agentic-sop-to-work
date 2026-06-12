# 轉換 SOP：Human SOP → 工具 Skill → Agentic Workflow（可分享 / 跨環境 / 跨專案重用）

## 批次 map（map_over，循序 fan-out）
工具步驟可加 `map_over: "<key>"`（指向**輸入 artifact data 的頂層清單鍵**）：引擎對清單**每一項**各跑一次該工具（依序、隔離），把每次輸出的 `data` 收進 `map@1` artifact 的 `data.items`（並附 `data.count`）。
`{"skill":"check","tool":"skills/check/tool.py","map_over":"items","in":"$RUN/x.json","out":"$RUN/y.json"}`
- **fail-loud**：任一項失敗即整步失敗（不靜默丟）。可在 map 步驟掛 `gate`（如 `recompute_gate` 驗 `count`）。
- 鍵為頂層、循序執行（並行屬 YAGNI、未做）。

## 條件分支（branch，forward-only）
flow.json 可放分支步驟，依**上一步 artifact 的 data** 由程式（非模型）決定走向：
`{"branch":"$RUN/c.json","cases":[{"when":{"path":"severity","op":"==","value":"OOS"},"goto":"investigate"},{"default":true,"goto":"release"}]}`
- `goto` 對應某步的 `skill`/`id`，且**只能往前跳**（forward-only）→ 無迴圈、確定性。
- 運算子白名單：`== != < <= > >= in exists`；型別不符回 false、不丟例外。
- 複雜判斷可由一支確定性 router skill 輸出 `data.route`，再用 `{"path":"route","op":"==",...}` 分流。

## 執行期硬閘門（lib/gates.py）與步驟型態
flow.json 每步可選掛 deterministic 閘門（產出後驗、fail 即停）：
`cmd_gate`（指令 exit 0）/ `schema_gate`（必填欄位）/ `trace_gate`（值須 verbatim 溯源、防臆造）/ `recompute_gate`（數字重算相符）。
指令型步驟：`{"cmd":"...","out":"...","gate":{"type":"cmd_gate"}}`；會改動環境的標 `"mutates":true`，需 `--allow-mutations` 才跑。
`python3 workflow/run.py --plan` 先列出所有操作（不執行），mutating 操作會標示。

本 kit 是一份**可複製到任何專案就能用**的轉換方法論 + 可運行範例。三個階段、各有**固定產物**與**交接介面**；
無硬編碼、依賴完整宣告（缺項明確報錯）。範例流程 `extract → compute → report` 是本 SOP 的 worked instance。

> 可攜性原則：所有路徑相對 kit 解析（`lib/kit.py::KIT_ROOT`，可被 `SOPKIT_ROOT` 覆寫）；專案專屬值一律參數化。

```
Human SOP ──(階段1: 記錄)──▶ 一份 SOP（固定模板）
            ──(階段2: 拆解規則)──▶ N 個單一工具 skill（各自依賴/參數化/I-O 介面）
            ──(階段3: 編排)──▶ flow.json + run.py + hook + slash command（A→B→C 自動串接）
```

---

## 階段 1 — Human SOP（以固定模板記錄人工流程）

產物：一份依 **`templates/human_sop_template.md`** 填寫的 SOP，**必含**：
1. **目的**（這份流程要達成什麼）
2. **前置條件**（開始前需具備的輸入/狀態/權限）
3. **逐步操作**（每一步：做什麼 + **用哪個工具**）
4. **判斷點**（哪裡需要分支/人為決定，條件為何）
5. **完成條件**（怎樣算完成、產物是什麼）

> 「每步用哪個工具」是階段 2 拆解的依據——一步一工具。

**這份產物怎麼來（intake 分流）**
- 使用者已給**正式 spec／既有 requirement 或 runner skill／已填好的本模板** → **照原樣採用**，直接進階段 2。
- 只有**自然語言需求** → 由 Claude 依本模板**起草** SOP（未知標【待補】、不臆造），**STOP 給人核准/修改**後再進階段 2。
- 草稿 SOP 是 **DRAFT**；此步屬生成層，**閘門/引擎不變**。

---

## 階段 2 — 工具 Skill（依拆解規則切成數個單一工具 skill）

### 拆解規則（Decomposition Rules）
1. **一 skill 一工具**：SOP 中每個「用到某工具」的步驟 → 一個 skill。跨工具的步驟必須再拆。
2. **依賴自足且完整**：每個 skill **只宣告自己那個工具**的依賴（工具/模組/環境變數/權限），且**列全**；
   執行時以 `kit.require_deps()` 檢查，**缺任一項明確報錯（拋 `MissingDeps`），絕不靜默失敗**。
3. **零硬編碼**：所有專案專屬值（路徑、專案名、設定）一律參數化（`--in/--out`、環境變數、config），程式內不得寫死。
4. **明確 I/O 介面**：定義與上下游 skill 交換的資料格式（本 kit 用 JSON **artifact**：`{schema, produced_by, data, trace}`）。
5. **可獨立抽出重用**：`skills/<name>/` + `lib/kit.py` 複製到別專案即可單獨運作（無專案耦合）。
6. **納入即登記測試**：每新增一個 skill，**同步**寫一支單元測試並登記到 **`tests/registry.json`**（受測功能登錄表）。
   `tests/verify.py` 會交叉比對 `flow.json`——任何流程用到卻未登記測試的 skill 會 **fail-loud（exit 3）**，杜絕「加了 skill 卻忘了測」。

### 每個 skill 的產物
- `skills/<name>/SKILL.md`：宣告**單一工具**、**完整依賴**、**參數化介面**、**I/O schema**、**獨立重用**說明。
- `skills/<name>/tool.py`：頂層宣告 `DEPS`；`if __name__=='__main__': kit.skill_main(DEPS, WHO, run)`（自動 require_deps + 解析 `--in/--out`）。
- `tests/unit/test_<name>.py`：該 skill 的單元測試；並在 `tests/registry.json` 的 `skills.<name>` 登記其 `dir` 與 `tests`。
- 範本：`templates/skill_template/`。範例：`skills/extract|compute|report/`。

---

## 階段 3 — Agentic Workflow（編排層 + hook + slash command）

把零散的單一工具 skill **依 SOP 實際順序**串成完整流程：
- **`workflow/flow.json`**：宣告順序與 I/O 接線（`$INPUT`、`$RUN` 佔位；上一步 `out` = 下一步 `in`）。
- **`workflow/run.py`**：逐步以子程序跑各 skill、串接 artifact、產 run-scoped `run_manifest.json`、**人核准 STOP**；任一步失敗（含缺依賴）→ 立即停止、回報該步 stderr。 失敗時 manifest 帶 `failure{step,gate_type,message,artifact}`；`/sop-flow` 據此做**封頂自動修復**（同 run-id ≤ `--max-fix-retries` 次，程式強制上限），終點仍 DRAFT＋人核准。
- **`commands/sop-flow.md`**：slash command，讓 agent 在目標專案 `/sop-flow` 觸發流程。
- **`hooks/settings.snippet.json`**：hook 設定。
  - **SessionStart**：跑 `check_deps.py`，缺依賴在 session 開場就明確報錯。
  - **Stop**（自動回歸驗證）：`hooks/stop_regression.py` 在 agent 準備停止時跑 `tests/verify.py`——見下節。

---

## 自動回歸驗證（更新不弄壞既有功能）

每次 SOP/skill 更新後，由 **Stop hook** 自動把關，流程全自動：
- **受測功能登錄表 `tests/registry.json`**：每個 skill 的單元測試 + 整條 workflow 的整合測試的單一事實來源。
- **`tests/verify.py`**：
  1. **變更偵測**（內容雜湊快照，不依賴 git、跨環境可用）：自上次「通過」後 SOP/任一 skill/編排層無變動 → 直接結束、不跑測試。
  2. 有變動 → 跑**兩層**：單元層（**受影響** skill 各自的測試；動到 `lib/`、`workflow/`、`registry.json` 等共用層則全跑）＋整合層（整條 workflow 串接、交接資料正確、失敗會傳播）。
  3. 寫**回歸紀錄** `tests/regression_log.jsonl`（時間、變更項、pass/fail、指標）。
  4. **判定**：全 pass = 正常（放行）；任一 fail → exit 2。「更好」指標（步數/時間/成功率）只記入 log，由人回看趨勢，hook 不自動下結論。
- **`hooks/stop_regression.py`**（Stop hook）：
  - 全 pass / 無變更 → 放行停止。
  - 任一 fail → 以 `{"decision":"block","reason":…}` 把失敗詳情餵回 agent 去修；保留紀錄供人決定修正或回滾。
  - **防迴圈**：用 Stop hook 輸入的 `stop_hook_active` 旗標 + 持久重試計數設上限（`SOPKIT_MAX_FIX_RETRIES`，預設 3），達上限即停止再 block、改要求人工介入，杜絕「失敗→修→再觸發→再失敗」無限循環。

> 手動全量驗證：`python3 tests/verify.py --all`（忽略變更偵測，建立基線/全跑）。

---

## 交接介面（Handoff Interface）規格
所有 skill 間以 JSON **artifact** 交換：
```json
{"schema": "<name@version>", "produced_by": "<skill>", "data": { ... }, "trace": [ {"value","source","locator"} ]}
```
- `schema` 標版本，便於相容性檢查；`data` 為該步結果；`trace` 為來源追溯（逐層透傳）。
- 範例鏈：`readings@1`（extract）→ `stats@1`（compute）→ Markdown DRAFT（report）。

---

## 驗收（本 kit 已自證）
- **(a)** 整包複製到全新空白專案，**不改任何程式** → `python3 agentic-sop-kit/workflow/run.py` 跑通範例流程。
- **(b)** 見 `README.md`（分享/安裝說明），未參與開發者照做即可安裝使用。
- **(c)** `python3 agentic-sop-kit/check_deps.py` 彙總所有依賴；缺項**明確列出並 exit 1**（非靜默）。

## 用本 kit 新建一條流程（A→B→C…）
1. 用 `templates/human_sop_template.md` 寫下你的 Human SOP（標出每步工具）。
2. 依拆解規則，每個「步驟×工具」用 **`python3 new_skill.py --name <name>`** scaffold 出 `skills/<name>/`（自動去 `.tmpl`、替換名稱、建單元測試骨架並登記 `tests/registry.json`）；接著填 DEPS / I-O / run()。（也可手動複製 `templates/skill_template/`。）
3. 在 `workflow/flow.json` 按 SOP 順序列出 steps 與接線。
4. `python3 check_deps.py` → `python3 workflow/run.py` 驗證；安裝 `commands/` + `hooks/` 讓 agent 觸發。
5. **完成工具後**，用 **`python3 export_claude_skill.py --skill <name> --project .`**（或 `--all`）產出可被 Claude 載入、對話即可觸發的 **runner skill**（寫到 `.claude/skills/`）——它只去執行你那支確定性工具並回報 DRAFT，不讓模型自行重做（守住控制流鐵則）。導入時加 `bootstrap.py --with-claude-skills` 會順便產生；要收回已產生的 runner skill，用 `export_claude_skill.py --remove --skill <name> --project .`（或 `--all`，只刪本工具產生的、手改過的會被拒絕除非 `--force`）。

## 目錄結構
```
agentic-sop-kit/
  SOP.md                      # 本檔（方法論）
  README.md                   # 分享/安裝說明（驗收 b）
  check_deps.py               # 聚合依賴檢查（驗收 c）
  requirements.txt            # 依賴清單（範例純 stdlib）
  lib/kit.py                  # 可攜核心（路徑解析/依賴/artifact/編排進入點）
  templates/                  # human_sop_template.md + skill_template/
  skills/<name>/              # 單一工具 skill（SKILL.md + tool.py）
  workflow/flow.json,run.py   # 編排層
  commands/sop-flow.md        # slash command
  hooks/settings.snippet.json # hook 設定（SessionStart 依賴檢查 + Stop 自動回歸）
  hooks/stop_regression.py    # Stop hook：自動回歸驗證 + 防迴圈
  tests/registry.json         # 受測功能登錄表（skill→單元測試；整合測試）
  tests/unit/, tests/integration/  # 單元層 / 整合層測試
  tests/verify.py             # 變更偵測→兩層測試→回歸紀錄→判定
  tests/regression_log.jsonl  # 回歸紀錄（執行後生成）
  example/inputs/             # 範例輸入
  runs/<run_id>/              # run-scoped 產物（執行後生成）
```

## 跨領域範例（workflow/examples/）
四個免依賴範例流程證明「同一引擎、四領域都跑得起來」：`fe.json`(cmd_gate)、`be.json`(schema_gate)、`db.json`(recompute_gate)、`ai.json`(trace_gate)。
跑：`python3 workflow/run.py --flow workflow/examples/be.json`（先 `--plan` 看操作）。詳見 `workflow/examples/README.md`。
