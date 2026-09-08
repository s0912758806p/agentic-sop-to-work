# Changelog

All notable changes to **agentic-sop-kit** are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/); the project follows [Semantic Versioning](https://semver.org/).

## [1.10.0] — 2026-09-08
### Added
- **Graph Engineering** — the tier above Loop Engineering: Loop Engineering makes **one** loop trustworthy; this composes trustworthy loops into a **bounded graph**. Nodes are steps (a node is *not* an agent — `one skill, one tool` is unchanged), edges are typed handoff contracts, and state is a declaration rather than a container. Every *feature* is **opt-in**: a flow declaring none of `reads` / `writes` / `schema_ref` / `back` produces **byte-identical artifacts and the same manifest key set** as v1.9.0, guarded by `tests/integration/test_legacy_flow.py`. The one thing that is not opt-in is topology legality — see **Breaking**.
- **Typed handoff edges** (`kit/lib/schema.py` + `kit/workflow/schemas/*.json`) — `artifact["schema"]` was decorative (`kit.artifact()` never validated it and `schema_gate` never read it). A step may now declare `gate.args.schema_ref`, and a wrong tag or wrong `data` shape is a hard failure. Minimal stdlib validator (required fields + `list/dict/str/number/bool`), deliberately **not** JSON Schema — the stdlib-only invariant is machine-enforced. Without `schema_ref`, `schema_gate` behaves exactly as before.
- **Static topology validation** (`kit/lib/graph.py`) — `run.py --plan` now analyses the whole graph and exits 2 on: unreachable node, read-before-write, write conflict, unbounded cycle, back-edge declared-but-forward, back-edge missing its bound, backward `goto` without a declaration, dangling `goto`, missing `goto`, ambiguous duplicate name, malformed step. An illegal topology is known **without running it**. `analyze()` is the single authority and **the runtime enforces exactly what `--plan` reports** — there is no per-flow exception list.
- **Bounded back-edges** — a backward `goto` is legal only as `{"back": true, "max_revisits": N}`. This replaces the forward-only rule's **prohibition** with a **bound**; determinism is unchanged because every cycle must pass through a bounded edge. Crucially it unlocks machinery that already shipped: `kit/lib/loop/`'s progress sensor now measures **per edge**, so identical routing state across revisits is an `idle` stall that stops the loop *before* the bound (dual termination, whichever fires first). Hitting the bound writes `revisit_exhausted` + `back_edge` and STOPS — it never falls through.
- **State as a declaration, not a container** — `reads` / `writes` per step, with **exactly one declaring writer per field** and a guaranteed write on every path to a reader. There is no `state.json`, so nothing can drift from the artifacts: a field's value stays in its owner node's artifact and `written_by` is that artifact's own `produced_by`. The run manifest records `topology` (field owners, back-edges and their bounds) and `path_taken` (the walk actually performed, with visit numbers). A revisit **archives** the previous artifact (`draft.visit1.json`) instead of overwriting it, so retry history survives — the reason a declaration was chosen over a central store that overwrites.
- **`residual_gate`** — the kit finally scans its own output for `【待補】`. A field declared `required` that is missing or still holds the placeholder is a hard failure; the marker anywhere else is a legitimate honest blank and never blocks. (Previously alcoa-guard checked required fields of a different input and second-opinion let the placeholder pass — nothing checked the kit's own output.)
- **`run.py --graph`** — renders the topology as Mermaid, deterministically (back-edges dotted).
- **`workflow/examples/graph.json`** + three demo skills (`draft` / `verdict` / `accept`) — a four-node review loop with a real bounded back-edge, typed edges on every step, and unique field ownership; converges in three rounds using its declared 2 revisits. `accept` refuses a rejected draft regardless of how routing reached it (a gate checks truth, not who called it).
- **First docs-freshness test** (`kit/tests/test_graph_docs.py`) — the repo had none. The topology diagram in `README.md`, `kit/README.md` and `kit/SOP.md` is **generated from `flow.json` and byte-compared**, and the documented gate count and gate names are bound to `gates.REGISTRY`. **Fail-closed**: a missing generated-block marker turns the test RED rather than silently passing.

### Changed
- **`agentic-workflow-audit`** — reframed around graph properties: 6 checks → **7** (new: *is the topology drawable and legal?*) and 2 litmus tests → **3** (new: *draw the graph from declarations, then check the real run only walked edges that exist on it*). Check 2's FAIL text is **unchanged** — a distinction was added beneath it: a shared state is a blackboard only when it has **no contract**, and named typed edges + a unique declaring writer + a guaranteed write on every path *are* that contract. Check 6 became "is there a failure edge, and is it bounded?". New red line: never fail a design merely for having shared state or a cycle — demand the evidence of a contract or a code-enforced bound instead. **The doctrine got sharper, not looser.**
- **`agentic-sop`** — a "declare the topology" step now sits between decomposition and wiring: name the nodes, name and type every edge, assign one owner per state field, declare the back-edge and its bound, then validate with `--plan`. Iron rules gained "a shared state needs a contract" and "a cycle must be bounded".
- **`kit/SOP.md`** — stage 3 is now *topology declaration*; decomposition gained rule **7** (declare `reads`/`writes`); the handoff-interface section documents the schema registry. The forward-only rule (`goto` 只能往前跳 → `無迴圈`) is **superseded**: cycles are legal when bounded.
- `print_plan` now renders from `graph.analyze`'s model instead of re-deriving its own checks (one authority, not two); it also prints per-node `emits` / `reads` / `writes` and the field-owner table.
- README: added the Graph Engineering tier and the generated topology; fixed two pre-existing drifts — `second-opinion-honesty` was missing from the "what you get" table, and the skills badge said 3 (the marketplace ships 6).
- Registered-test count 19 → 30 (the coverage ratchet rises accordingly).
- Only schemas that are actually enforced ship: `workflow/schemas/` carries the three tags `graph.json` gates on (`draft@1` / `verdict@1` / `accepted@1`). Declaring `readings@1` / `stats@1` / `map@1` / `cmd@1` up front would ship documents nothing checks — the linear demo must stay byte-identical, so it will never use a typed edge.
- `test_health_gate.py` runs its disposable kit copy against a **minimal registry**. The health gate judges a count against a baseline, so which tests are registered is irrelevant to it; this meta-test invokes `verify.py` 7+ times, and the change takes it from ~150s to ~10s without weakening the assertion (it still requires `HEALTH(hard)` for the right reason).

### Removed
- `run.py --state` and `graph.ascii_view()`. Both were presentation over data that is already available: `--plan` prints the field-owner table before a run, and the manifest's `topology` / `path_taken` carry owners, visit numbers and archived attempts after one. Note the honest cost: nothing now reads an artifact's `produced_by` at runtime, so "written_by is produced_by" is a documented property rather than a code-verified one.
- Five test cases that were not testing real behaviour: three asserted a hand-written fixture against a hand-written schema (both mine — a tool changing shape would not have been caught; the real coverage is `graph.json` running the real tools through `schema_gate`), and two bound a documented number by string-splitting `graph.py`'s source. Registered-test *file* count — what the coverage gate actually measures — is unchanged.

### Breaking
- **An illegal topology now refuses to run for every flow, not just graph-declaring ones.** Previously the runtime held a flow that declared no graph features to only what the pre-graph engine refused, printing the newer findings as advisory. That split was one concept to maintain and made `--plan` and the runtime disagree about strictness. The only case that changes in practice: a flow with an **unreachable step** (a step no path can reach) now stops with `topology_invalid` instead of a warning. Fix by deleting the dead step or wiring it up; `--plan` names it exactly.

## [1.9.0] — 2026-06-23
### Added
- **Six-Rung Ladder skill** (`six-rung-ladder`, agentic-sop-kit → v1.9.0) — a triggerable minimalist decision filter for "should I write this code / add this dependency / introduce this abstraction?": YAGNI → Stdlib → Native platform → Installed dep → One line → Minimum-that-works, stopping at the first rung that resolves. Rungs 2 & 4 (stdlib / no-new-dep) route to the existing `test_no_third_party` + `plugin-forge lint` gates; the red line (defensive code — injection / resilience / security — never skipped) maps to the existing iron rule. Completes the methodology trio: **decide → build (`agentic-sop`) → audit (`agentic-workflow-audit`)**. Pure docs — no new code/deps.
- **Bounded run-state** (Loop Engineering cut #3) — a deterministic policy (`kit/lib/loop/state.py`) keeps the kit's run-state bounded: `verify.py` **auto-rotates** `regression_log.jsonl` to the last `SOPKIT_STATE_KEEP_LOG` (200) lines, never below a fixed floor (50) that protects the cut #2 health windows; `run.py --prune` **(human-authorized)** evicts run dirs beyond `SOPKIT_STATE_KEEP_RUNS` (20), keeping the newest (in-flight runs are never evicted). `run.py` prints a non-destructive advisory when over the limit. Pure stdlib.
- **Runtime health monitoring** (Loop Engineering cut #2) — a deterministic reader (`kit/lib/loop/health.py`) over the regression-run history: **coverage shrink** (registered-test count below baseline) hard-gates via `verify.py` exit 3 (rides the existing Stop-hook block); **slowdown** and **flaky** surface as advisory only (never gate). Coverage baseline ratchets up automatically; intentional drops use `verify.py --rebaseline`. Knobs `SOPKIT_HEALTH_SLOWDOWN_FACTOR` (2.0), `SOPKIT_HEALTH_FLAKY_WINDOW` (10). Pure stdlib.
- **stall detection** (agentic-sop-kit → v1.6.0) — Loop Engineering cut #1: deterministic, zero-LLM progress-based early-stop in the fix-loop. No verifiable progress (idle, or A→B→A thrash) → hard stop + refuse re-runs, mirroring the budget ceiling. New `kit/lib/loop/` package + `SOPKIT_STALL_WINDOW` (`--stall-window`, default 2; 0 disables; cycle cap fixed at 2). Pure stdlib.
- **plugin-forge** (v0.1.0) — new companion plugin: Claude Code plugin linter + scaffolder.
  Its `lint --all --strict` replaces `validate_manifests.py` in CI (strict superset). Pure stdlib.
- **alcoa-guard** (v0.1.0) — new companion plugin: deterministic ALCOA+ data-integrity linter
  (Attributable / Contemporaneous / Complete / Accurate / Consistent), DEGRADED + FULL modes,
  human-judgment checklist, pure stdlib. Enforcing Stop-hook deferred to v0.2.

## [1.5.4] — 2026-06-12
### Added
- **Smart intake** for `agentic-sop` — classifies the input on trigger: a written spec / existing skill / filled SOP → use as-is; a natural-language need → Claude drafts a Human SOP (gaps `【待補】`, no fabrication), pauses for human confirm, then continues to decomposition. (Generative layer only; gates + DRAFT+human spine unchanged.)
- **Capped auto fix-loop** — `run.py` emits a machine-readable `failure{step,gate_type,message,artifact}`, and `/sop-flow` auto-fixes & re-runs on a gate failure, capped by `run.py --max-fix-retries` (default 3, **code-enforced** per run-id → `fix_exhausted`); exhausted → stop for a human; never patches output to pass. Shares one cap knob `SOPKIT_MAX_FIX_RETRIES` (default 3) with the Stop-hook regression loop — two layers, one setting. Adds `tests/integration/test_fix_loop.py`.
### Changed
- README "At a glance" is now an **animated step-by-step flow GIF** (`assets/flow.gif`, generated by `assets/flow/make_flow_gif.py` — Pillow, deterministic); the static Mermaid diagram moved into a `<details>` fallback. Depicts intake routing + the capped fix-loop.

## [1.5.3] — 2026-06-12
### Changed
- Rewrote the `agentic-sop` and `agentic-workflow-audit` skill **descriptions** to CSO (Claude-Search-Optimization) form: lead with `Use when…`, drop the embedded process summary, add reciprocal `不適用` disambiguation between the two skills, ~45% shorter (642→331 and 587→379 chars). Improves auto-trigger discoverability and eases skill-catalog description-budget pressure. A/B routing trials showed no regression; regression suite 14/14.
- Added this `CHANGELOG.md`.

## [1.5.2] — 2026-06-11
### Changed
- Extracted the SOP orchestration engine (`run_step` / `run_map` / `print_plan`) from `run.py` into `kit/lib/engine.py`; slimmed `run.py` to orchestrator-only.
- Bilingual (EN / 中文) engine error messages; expanded `--plan` documentation.

## [1.5.1] — 2026-06-11
### Fixed
- `--plan` now renders `branch` / `map` steps and **statically validates** branch `goto` targets (forward-only, must exist, no duplicates); duplicate step-name flagged only at the `goto` site; malformed steps flagged; missing `goto` handled. Added backward-goto and duplicate-name tests.

## [1.5.0] — 2026-06-10
### Added
- Phase C: dependency-free FE / BE / DB / AI example flows (one gate each) under `kit/workflow/examples/`, registered as a test; documented examples.

## [1.4.0] — 2026-06-10
### Added
- Phase B-map: sequential `map_over` (fan-out) with fail-loud per-item handling.

## [1.3.0] — 2026-06-10
### Added
- Phase B: forward-only conditional branching (`branch` / `cases` / `goto`); linear flows unchanged.

## [1.2.0] — 2026-06-10
### Added
- Phase A: per-step gates + `cmd` step + `--flow` / `--plan` / `--allow-mutations`. Deterministic hermetic gates (`cmd_gate` / `schema_gate` / `trace_gate` no-fabrication / `recompute_gate`); engine kept stdlib-only (neutrality-invariant test).

## [1.1.1] — 2026-06-10
### Added
- `skill-export --remove` to take back generated runner skills.

## [1.1.0] — 2026-06-10
### Added
- `skill-export` + `new-skill` generators, `/sop-flow` open-the-box demo, CI.

## [1.0.1] — 2026-06-09
### Added
- MIT LICENSE; owner/author set; attribution & provenance hardening (per-file headers, `NOTICE`, `SECURITY.md`, signed commits).

## [1.0.0] — 2026-06-09
### Added
- Initial public release: `agentic-sop` + `agentic-workflow-audit` methodology skills, the portable agentic-sop-kit, and the marketplace publish.

[1.10.0]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.10.0
[1.9.0]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.9.0
[1.5.4]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.5.4
[1.5.3]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.5.3
[1.5.2]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.5.2
[1.5.1]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.5.1
[1.5.0]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.5.0
[1.4.0]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.4.0
[1.3.0]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.3.0
[1.2.0]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.2.0
[1.1.1]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.1.1
[1.1.0]: https://github.com/s0912758806p/agentic-sop-to-work/releases/tag/v1.1.0
[1.0.1]: https://github.com/s0912758806p/agentic-sop-to-work/commit/4dfe104
[1.0.0]: https://github.com/s0912758806p/agentic-sop-to-work/commit/52e57e4
