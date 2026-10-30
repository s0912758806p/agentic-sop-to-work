# Contributing

This repo is a Claude Code plugin marketplace: four **stdlib-only** Python plugins. Every hard gate is
deterministic code; prose is never the enforcement. Read this before opening a PR.

## Layout and ownership

| Path | What | Notes |
|---|---|---|
| `plugins/agentic-sop-kit/` | the kit (writer of the run-dir contract) | engine in `kit/sopkit/`; `kit/lib/` is a deprecated shim (removed in v2.0) |
| `plugins/second-opinion-honesty/` · `alcoa-guard/` · `plugin-forge/` | companion plugins (readers / linters) | each ships a **vendored** `<pkg>/_core/` |
| `shared/sopcore/` | single source of the companions' shared core | edit here, never in `_core/` |
| `tools/sync_core.py` | vendors `shared/sopcore/` + shared test harness into each companion | |
| `tests/` | repo-level gates: docs freshness, sopcore, run-dir contract | |

## Rules that CI enforces

- **Stdlib only.** `plugin-forge lint --all --strict` and each plugin's `test_no_third_party.py` reject third-party
  imports and cross-plugin imports. A plugin may import only the standard library and its own package (incl. `_core/`).
- **Vendored core never drifts.** After editing `shared/sopcore/`, run `python3 tools/sync_core.py` and commit the
  regenerated `_core/` copies. CI runs `sync_core.py --check` and plugin-forge's HARD rule `vendored-core-drift`.
- **Docs stay true.** `tests/test_docs_freshness.py` binds README skill counts, CHANGELOG version entries, the
  marketplace plugin list and `SOPKIT_*` docs to the tree — fail-closed. Change behavior → update the living docs
  (README EN + 繁中, plugin README, `kit/README.md`, `kit/SOP.md`, file-header comments) **in the same commit**.
- **Run-dir format is a contract.** The kit writes it, companions read it through `shared/sopcore/run_contract.py`.
  `tests/test_run_contract.py` and `kit/tests/integration/test_golden.py` fail on any change.

## Running the checks locally (mirrors CI)

```bash
python3 plugins/plugin-forge/pluginforge/lint.py --all --strict
python3 tests/test_docs_freshness.py
python3 tools/sync_core.py --check
python3 plugins/agentic-sop-kit/kit/tests/verify.py --all
python3 plugins/agentic-sop-kit/kit/tests/test_verify.py
python3 plugins/agentic-sop-kit/kit/tests/test_stop_hook.py
python3 plugins/agentic-sop-kit/kit/tests/test_plugin_hooks.py
python3 plugins/agentic-sop-kit/kit/tests/integration/test_health_gate.py
python3 tests/test_sopcore.py
python3 tests/test_run_contract.py
python3 plugins/second-opinion-honesty/tests/verify.py
python3 plugins/alcoa-guard/tests/verify.py
python3 plugins/plugin-forge/tests/verify.py
claude plugin validate . --strict   # optional locally; advisory in CI
```

The kit meta-tests are deliberately **not** in `kit/tests/registry.json` (verify-in-verify recursion), so they only
run when called explicitly — CI does.

## Versioning

- Each plugin has its own SemVer in `.claude-plugin/plugin.json`. Bump it on every user-visible change; the version
  is pinned, so an unbumped change never reaches users.
- Every version needs a CHANGELOG entry: the kit as a `## [x.y.z]` heading, companions as `**<name>** (vx.y.z)`
  (the docs-freshness test checks both). New work goes under `## [Unreleased]`.
- **Two-stage policy.** v1.x is **zero-break** for users: replace, shim, and emit a `DeprecationWarning` or notice.
  Removals are collected for v2.0 in [`MIGRATION.md`](MIGRATION.md).
- Companion output changes (e.g. a stricter check) are allowed in a minor bump, called out under **Behavior changes**.

## Release procedure

1. **Stamp PR** (`chore/release-vX.Y.Z`): move `[Unreleased]` entries under the tag that first contains them, add
   the link ref, merge.
2. **Annotated tags** on `main`:
   - kit: `vX.Y.Z` — on the stamp PR's merge commit for the newest version, on the merge commit that introduced
     the version otherwise.
   - companions: `<plugin>-vX.Y.Z` (e.g. `alcoa-guard-v0.3.0`) on the merge commit that introduced the version.
3. **GitHub release** per tag (`gh release create <tag> --notes …`), notes summarized from the CHANGELOG. The newest
   kit release is marked Latest.

Users pick up a release with `/plugin marketplace update agentic-sop-to-work`, then `/reload-plugins`.

## Commits and PRs

Conventional-commit prefixes (`feat(scope):`, `fix(scope):`, `chore(release):`, `docs:`). One concern per PR; PRs are
merged with a merge commit.
