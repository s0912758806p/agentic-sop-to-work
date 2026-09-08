# agentic-sop-to-work

[![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=claude&logoColor=white)](https://claude.com/claude-code) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fs0912758806p%2Fagentic-sop-to-work%2Fmain%2Fplugins%2Fagentic-sop-kit%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue&prefix=v)](plugins/agentic-sop-kit/.claude-plugin/plugin.json) [![Skills](https://img.shields.io/badge/skills-6-8A2BE2)](plugins)

> **Loop Engineering** — make an agent's loop produce **verifiable progress**, stay **honest**, and stay **bounded**, by deterministic mechanism rather than vibes. `agentic-sop-kit` is the reference toolkit: it turns a human SOP into a **controlled loop**, not a one-shot script — no fabrication, no "mega-agent" rot.
> **Loop Engineering** — 用確定性機制(不是 vibes)讓 agent 的迴圈**每次迭代產生可驗證進度、不自我欺騙、不失控**。`agentic-sop-kit` 是它的參考工具包:把人工 SOP 變成一條**受控迴圈**——不臆造、不退化成 mega agent。
>
> **⭘→◉ Graph Engineering — when one loop isn't enough.** Loop Engineering makes **one** loop trustworthy; Graph Engineering composes trustworthy loops into a **bounded graph**: named nodes, **typed handoff edges**, field-level state ownership, and **bounded back-edges**. The loop invariants descend to nodes and edges — same determinism, one rung up.
> **⭘→◉ Graph Engineering — 一個迴圈不夠用時。** Loop Engineering 讓**一個**迴圈可信；Graph Engineering 把可信的迴圈接成一張**有界的圖**:具名節點、**有型別的交接邊**、欄位級的狀態所有權、**有界退回邊**。三個不變量下降到節點與邊的粒度——確定性不變,只是上了一階。

```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install agentic-sop-kit@agentic-sop-to-work
/reload-plugins
```

**🌐 [English](#english) ・ [繁體中文](#繁體中文)**

### 🗺️ At a glance · 運作一覽

![Agentic-SOP flow — Human SOP → single-tool skills → run.py → per-step gate → DRAFT → human approval, with a Stop-hook regression gate guarding every change](assets/flow.gif)

*Human SOP → single-tool skills → orchestrated flow (gated · branch · map) → DRAFT → human approval; a Stop-hook regression gate guards every change.<br>Human SOP → 單一工具 skill → 編排流程（閘門・分支・map）→ DRAFT → 人核准；Stop-hook 回歸閘門守住每次變更。*

<details>
<summary>靜態圖 / static diagram</summary>

```mermaid
flowchart LR
    SOP["📄 Human SOP"]
    SK["🔧 single-tool skills<br/>one tool · I/O contract"]
    RUN["⚙️ run.py<br/>steps · branch · back-edge · map · --plan"]
    G{{"🚦 per-step gate<br/>cmd · schema · trace · recompute · residual"}}
    DR["📝 DRAFT"]
    OK(["✋ human approval"])
    STOPN["✗ stop & fix"]
    REG[["🔁 Stop-hook regression<br/>change → tests → block & fix"]]

    SOP -- decompose --> SK
    SK -- orchestrate --> RUN
    RUN --> G
    G -- pass --> DR
    DR --> OK
    G -- fail --> STOPN
    G -. bounded back-edge .-> RUN
    REG -. guards every change .-> SK

    style OK fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20
    style G fill:#FFF8E1,stroke:#F9A825
    style REG fill:#FFEBEE,stroke:#C62828,color:#B71C1C
```

</details>

### 🔁 The loop, engineered · 受控迴圈的三不變量

`agentic-sop-kit` makes the loop a **controlled** one — three deterministic invariants, human-owned at the controlled/destructive edges:
- **Bounded termination · 有界終止** — budget (count) **+ stall (progress)**: stop when iterations stop producing verifiable progress, not only when retries run out.
- **Observable health · 可觀測健康** — a coverage drop **hard-gates**; slowdown / flaky surface as advisory.
- **Bounded state · 有界狀態** — the regression log auto-rotates; run dirs prune on demand (human-authorized).

*"Human SOP → workflow" is **one application** of this loop; the same loop-control applies to any agent loop.*

### ◉ The graph, engineered · 把迴圈接成一張有界的圖

A linear pipeline cannot express "the reviewer sent it back". A graph can — without giving up determinism:
一條線性管線無法表達「審查把它退回去了」。圖可以——而且不必放棄確定性:

- **Nodes are steps, not agents · 節點是步驟,不是 agent** — one node = one tool. Swap the tool for a model and people call it an agent, but `one skill, one tool` is unchanged. *節點就是「一個工具的一步」;`一 skill 一工具` 一個字不改。*
- **Typed edges · 有型別的邊** — `schema_ref` makes the `schema` tag load-bearing: wrong tag or wrong shape is a hard failure. An untyped edge means the handoff contract is fiction. *邊沒有型別,交接協定就是假的。*
- **State is a declaration, not a container · 狀態是宣告,不是容器** — no state store, so nothing can drift from the artifacts. A field's value stays in its owner node's artifact and `written_by` is that artifact's own `produced_by`. Exactly one declaring writer per field; the run manifest records `topology.owners` and `path_taken`. *唯一 writer + 所有路徑保證寫過,就是「誰給誰什麼」的契約——這是稽核條文「黑板式共享狀態 = FAIL」的可執行版本,條文本身一字未改。*
- **Cycles are legal because they are bounded · 環合法是因為有界** — a backward `goto` must declare `back:true` + `max_revisits`. `--plan` refuses an unbounded cycle before anything runs, and `lib/loop/`'s progress sensor now measures **per edge**: identical routing state across revisits is an `idle` stall that stops the loop *before* the bound. *舊的 forward-only 從「禁止」改成「有界才准」。*
- **Retry history survives · 退回歷史不被覆寫** — a revisit archives the previous artifact (`draft.visit1.json`) instead of overwriting it. *一個會覆寫的中央 store 會讓第一次嘗試消失。*

<!-- BEGIN GENERATED: topology -->
```mermaid
flowchart LR
    n0["draft<br/>draft@1"]
    n1["verdict<br/>verdict@1"]
    n2{{gate}}
    n3["accept<br/>accepted@1"]
    n0 --> n1
    n1 --> n2
    n2 -.->|"verdict == 'reject' (≤2)"| n0
    n2 -->|"default"| n3
```
<!-- END GENERATED: topology -->

*The shipped `graph.json` example, drawn by `run.py --graph`. This block is generated from the flow and byte-compared by `kit/tests/test_graph_docs.py` — the picture cannot disagree with the pipeline.<br>出貨的 `graph.json`,由 `--graph` 生成、由測試逐位元綁住——圖不可能與流程不一致。*

**Adopting nothing is free · 不宣告就零影響** — declare none of `reads` / `writes` / `schema_ref` / `back` and the engine behaves **byte-identically** to before, guarded by `test_legacy_flow.py`.

---

## English

**What.** `agentic-sop-kit` is a **Loop Engineering** toolkit: it turns a process you do by hand (a "Human SOP") into a **controlled agentic loop** an LLM can run safely and repeatably — with bounded termination, observable health, and bounded state. A methodology + portable toolkit — not a chatbot. Built for regulated / high-stakes / must-be-correct work.

**Why it's safe** — it blocks the predictable LLM failures:
- **Fabrication** → facts come only from inputs; gaps marked `【待補】`, never invented.
- **Fake autonomy** → deterministic work in code; hard gates are hermetic & LLM-free (self-eval only advisory, capped).
- **Unaccountable output** → every output is a **DRAFT**; controlled / high-risk calls stay human-owned.
- **Mega-agent rot** → an audit skill + a Stop-hook **regression gate** that re-verifies on every change.

**What you get**

| | |
|---|---|
| **3 Skills** (auto-trigger by intent) | `six-rung-ladder` — minimalist "should I build this at all?" filter (**decide**) · `agentic-sop` — methodology + entry point + smart intake (**build**) · `agentic-workflow-audit` — read-only mega-agent auditor (**audit**) |
| **Command** `/agentic-sop-kit:sop-flow` | runs the kit's orchestration, reports a DRAFT |
| **Hooks** (project-scoped) | `SessionStart` dep-check · `Stop` regression gate — **no-op until a project adopts the kit** |
| **Portable kit** `kit/` | copy-into-any-project methodology + runnable example |
| **Plugin** `second-opinion-honesty` | adversarial honesty reviewer — checks a finished DRAFT's claims against its evidence (fabrication / overreach / invented IDs); deterministic findings are HARD, the LLM red-team layer is advisory and capped; reads a run dir read-only, never imports the kit |
| **Plugin** `alcoa-guard` | ALCOA+ data-integrity linter — deterministic checks for Attributable / Contemporaneous / Complete / Accurate / Consistent; surfaces the human-judgment slice as a `【待補】` checklist; pure stdlib; report is a DRAFT |
| **Plugin** `plugin-forge` | Claude Code plugin linter + scaffolder — `lint` validates a plugin or whole marketplace against a house grammar (strict superset of manifest/frontmatter checks + stdlib-only, hook-protocol, and test-harness invariants); `scaffold` generates a grammar-conformant plugin skeleton; self-hosting; pure stdlib |

**Engine (`run.py`)** — deterministic, code-decided, additive:
- **Per-step gates** (block on fail, zero LLM): `cmd_gate` · `schema_gate` (+ `schema_ref` for a typed edge) · `trace_gate` (no fabrication) · `recompute_gate` · `residual_gate` (a required field still `【待補】`).
- **`cmd` steps** (allowlisted; mutations need `--allow-mutations`) · **`--plan`** dry-run — lists every step **and statically validates the whole topology** (unreachable node · read-before-write · write conflict · unbounded cycle · dangling goto), exit 2 before anything runs.
- **`branch`** · **bounded back-edges** (`back:true` + `max_revisits`) · **`map_over`** (per-item) — control flow in code, never the model.
- **`--graph`** draws the topology as Mermaid · the run manifest carries `topology` (field owners, back-edges and their bounds) and `path_taken` (the walk actually performed, with archived earlier attempts).
- **Examples** — dependency-free FE / BE / DB / AI flows plus a four-node `graph.json` with a real bounded back-edge, in [`kit/workflow/examples/`](plugins/agentic-sop-kit/kit/workflow/examples/).
- **Capped auto fix-loop** — on a gate failure, `/sop-flow` auto-fixes & re-runs (`run.py --max-fix-retries`; code-enforced per run-id, capped by `SOPKIT_MAX_FIX_RETRIES`, default 3 — the same knob as the Stop-hook regression loop); exhausted → stop for a human; never patches output to pass.
- **Loop control** (Loop Engineering, in [`kit/lib/loop/`](plugins/agentic-sop-kit/kit/lib/loop/)) — keeps the loop bounded, observed, and bounded-in-state: **stall** stops on no verifiable progress (`SOPKIT_STALL_WINDOW`); **health** hard-gates a coverage drop and flags slowdown/flaky (advisory); **state** auto-rotates the run log and prunes run dirs on demand (`run.py --prune`). All deterministic.

**Iron rules** — facts only from inputs (`【待補】` for gaps) · deterministic work in code, gates hermetic & LLM-free · DRAFT + human approval · gates check truth, not keywords · a shared state needs a contract: one declaring writer per field, guaranteed on every path. **Real enforcement is the Stop-hook and the static topology gate, not prose.**

**Install** — in Claude Code (incl. Claude Desktop's Code tab):
```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install agentic-sop-kit@agentic-sop-to-work
/reload-plugins      # or restart the session
```
Requires **Python 3.8+** as `python3` (macOS/Linux out of the box; on Windows ensure `python3` resolves). Verify: `/help` lists `/agentic-sop-kit:sop-flow`.

**Build your own flow** — adopt the kit: `python3 <plugin>/kit/bootstrap.py --project <dir>` → scaffold a step: `new_skill.py --name <x>` (fill `DEPS` / `run()`) → wire `workflow/flow.json` → make it conversation-triggerable: `export_claude_skill.py --skill <x>`. Details: [`kit/SOP.md`](plugins/agentic-sop-kit/kit/SOP.md).

**Layout**
```
agentic-sop-to-work/
├── .claude-plugin/marketplace.json
└── plugins/agentic-sop-kit/
    ├── .claude-plugin/plugin.json · skills/ · commands/ · hooks/
    └── kit/   # portable kit: lib/ · workflow/ · tests/ · templates/ · examples/ · SOP.md
```

**License** — MIT ([`LICENSE`](LICENSE) · [`NOTICE`](NOTICE)); keep the copyright/license notice in copies, including single files. Updating: `git push` → users run `/plugin marketplace update agentic-sop-to-work`; bump `plugin.json` `version` on each meaningful change.

---

## 繁體中文

**是什麼。** `agentic-sop-kit` 是一套 **Loop Engineering** 工具包：把你手動做的流程（Human SOP）工程化成 LLM 能**安全、可重複**執行的**受控 agentic 迴圈**——有界終止 ＋ 可觀測健康 ＋ 有界狀態。是一套方法論 ＋ 可攜工具包，不是聊天機器人。為受監管／高風險／不能錯的工作而生。

**為何可信** — 逐一封堵 LLM 的可預期失敗：
- **臆造** → 事實只來自輸入；缺的標 `【待補】`，絕不杜撰。
- **假自主** → 確定性的事用程式；硬閘門 hermetic、零 LLM（自評只能 advisory 且封頂）。
- **無人負責的產出** → 產出一律 **DRAFT**；受控／高風險判定永遠由人擁有。
- **mega-agent 退化** → 稽核 skill ＋ Stop-hook **回歸閘門**，每次變更重新驗證。

**你會得到**

| | |
|---|---|
| **3 支 Skills**（依意圖自動觸發） | `six-rung-ladder` —「到底該不該做」的極簡過濾網（**decide**） · `agentic-sop` — 方法論與入口＋智慧意圖分流（**build**） · `agentic-workflow-audit` — 唯讀的 mega-agent 稽核者（**audit**） |
| **指令** `/agentic-sop-kit:sop-flow` | 跑 kit 的編排、回報 DRAFT |
| **Hooks**（專案範圍） | `SessionStart` 依賴檢查 · `Stop` 回歸閘門 — **專案未導入 kit 前一律 no-op** |
| **可攜 kit** `kit/` | 複製到任何專案就能用的方法論 ＋ 可運行範例 |
| **Plugin** `second-opinion-honesty` | 對抗式誠實審查者 — 拿完成的 DRAFT 的宣稱去對它自己的證據（臆造／超譯／發明編號）；確定性發現為 HARD、LLM 紅隊層只能 advisory 且封頂；唯讀讀取 run 目錄，不 import kit |
| **Plugin** `alcoa-guard` | ALCOA+ 資料完整性 linter — 確定性檢查 Attributable／Contemporaneous／Complete／Accurate／Consistent；人判部分呈現為 `【待補】` checklist；純 stdlib；產出為 DRAFT |
| **Plugin** `plugin-forge` | Claude Code plugin linter + scaffolder — `lint` 依 house grammar 驗證單一 plugin 或整個 marketplace（manifest／frontmatter 檢查的嚴格超集＋stdlib-only、hook-protocol、test-harness 不變量）；`scaffold` 產生符合 grammar 的 plugin 骨架；自我宿主；純 stdlib |

**引擎（`run.py`）** — 確定性、由程式決定、附加式：
- **每步硬閘門**（fail 即停、零 LLM）：`cmd_gate` · `schema_gate`（加 `schema_ref` 即為有型別的邊）· `trace_gate`（防臆造）· `recompute_gate` · `residual_gate`（必填欄位仍是【待補】即擋）。
- **`cmd` 步驟**（白名單；會改動環境的需 `--allow-mutations`）· **`--plan`** 乾跑——列出每步**並靜態驗證整張拓撲**（不可達節點・read-before-write・寫入衝突・無界環・孤邊），不合法在跑之前就 exit 2。
- **`branch`** · **有界退回邊**（`back:true` ＋ `max_revisits`）· **`map_over`**（逐項）— 控制流由程式決定，不交給模型。
- **`--graph`** 畫拓撲（Mermaid）· manifest 帶 `topology`（欄位 owner、退回邊與上界）與 `path_taken`（實走路徑、被歸檔的前一次產物）。
- **範例** — 免依賴的 FE／BE／DB／AI 流程，外加四節點、含真的有界退回邊的 `graph.json`：[`kit/workflow/examples/`](plugins/agentic-sop-kit/kit/workflow/examples/)。
- **封頂自動修復 fix-loop**——閘門失敗時 `/sop-flow` 自動修復並重跑（`run.py --max-fix-retries`，依 run-id 程式強制上限；與 Stop-hook 回歸共用 `SOPKIT_MAX_FIX_RETRIES`、預設 3）；用盡才停下交人；永不為過關竄改輸出。
- **迴圈控制**（Loop Engineering，位於 [`kit/lib/loop/`](plugins/agentic-sop-kit/kit/lib/loop/)）——把迴圈維持**有界、可觀測、狀態有界**：**stall** 在無可驗證進度時早停（`SOPKIT_STALL_WINDOW`）；**health** 對覆蓋縮水硬擋、對變慢/flaky 給 advisory；**state** 自動輪替 run log、按需 `run.py --prune` 清理 run 目錄。全確定性。

**鐵則** — 事實只來自輸入（缺標 `【待補】`）· 確定性用程式、閘門 hermetic 零 LLM · DRAFT ＋ 人核准 · 閘門查真相不查關鍵字 · 共享狀態必須有契約：每個欄位唯一 writer、且所有路徑保證寫過。**真正的強制力在 Stop-hook 與靜態拓撲閘門，不在散文。**

**安裝** — 在 Claude Code（含 Claude Desktop 的 Code 分頁）：
```
/plugin marketplace add s0912758806p/agentic-sop-to-work
/plugin install agentic-sop-kit@agentic-sop-to-work
/reload-plugins      # 或重開 session
```
需 **Python 3.8+** 且能以 `python3` 呼叫（macOS／Linux 開箱即用；Windows 請確保 `python3` 可解析）。驗證：`/help` 應看到 `/agentic-sop-kit:sop-flow`。

**建你自己的流程** — 導入 kit：`python3 <plugin>/kit/bootstrap.py --project <dir>` → scaffold 一步：`new_skill.py --name <x>`（填 `DEPS` / `run()`）→ 在 `workflow/flow.json` 接線 → 讓它對話可觸發：`export_claude_skill.py --skill <x>`。詳見 [`kit/SOP.md`](plugins/agentic-sop-kit/kit/SOP.md)。

**結構**
```
agentic-sop-to-work/
├── .claude-plugin/marketplace.json
└── plugins/agentic-sop-kit/
    ├── .claude-plugin/plugin.json · skills/ · commands/ · hooks/
    └── kit/   # 可攜 kit：lib/ · workflow/ · tests/ · templates/ · examples/ · SOP.md
```

**授權** — MIT（[`LICENSE`](LICENSE) · [`NOTICE`](NOTICE)）；副本需保留版權／授權聲明，含單一檔案。更新：`git push` → 使用者跑 `/plugin marketplace update agentic-sop-to-work`；每次有意義變更調高 `plugin.json` 的 `version`。
