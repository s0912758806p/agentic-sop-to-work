# Changelog

All notable changes to **agentic-sop-kit** are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/); the project follows [Semantic Versioning](https://semver.org/).

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
