# Migration guide

> **Status: DRAFT for agentic-sop-kit v2.0 — not released.** Everything listed here still works in v1.x
> (the current line is v1.12.x) through shims, aliases or fallbacks. v1.x is zero-break by policy
> ([CONTRIBUTING.md](CONTRIBUTING.md#versioning)); v2.0 removes them. You can migrate **today** — every
> "do this now" step below already works on v1.12.

Companion plugins (second-opinion-honesty, alcoa-guard, plugin-forge) have no planned breaking changes.

## Planned removals in v2.0

| # | Removed in v2.0 | Deprecated since | What warns today | Do this now (works on v1.12) |
|---|---|---|---|---|
| 1 | `kit/lib/*.py` re-export shims | v1.11.0 | `DeprecationWarning` on `import kit` / `import gates` … from `kit/lib/` (visible with `-W default`) | In custom skill `tool.py` files, put the **kit root** on `sys.path` and `from sopkit import kit` (see `kit/templates/skill_template/tool.py.tmpl`) |
| 2 | Run dirs under `kit/runs` **inside the plugin cache** | v1.12.0 | a notice from `run.py` | Pass `--out-base <dir>`, or let the installed plugin use `$CLAUDE_PLUGIN_DATA/runs` (default since v1.12.0). A kit bootstrapped into a project keeps `agentic-sop-kit/runs/` — that is not affected |
| 3 | `kit/hooks/stop_regression.py` + `hooks/settings.snippet.json` registration in project settings | v1.10.1 | — (the plugin hook steps aside when it sees it) | With the plugin installed: delete the kit's `Stop` / `SessionStart` entries from `<project>/.claude/settings.json`; the plugin hooks take over. Without the plugin: keep `bootstrap.py --with-hooks` until v2.0 ships a replacement note |
| 4 | `bootstrap.py --no-hooks` | v1.10.1 | — (accepted, no-op: not writing hooks is the default) | Drop the flag |
| 5 | `graph._kind` / `graph._valid_bound` aliases, module attributes `kit.KIT_ROOT` / `schema.DEFAULT_DIR` | v1.11.0 | — | Use `graph.kind` / `graph.valid_bound` and `sopkit.config.kit_root()` / `SOPKIT_SCHEMA_DIR` |

## Under consideration (not decided)

These were discussed in the 2026-10 optimization plan and are **not** committed to v2.0:

- A `contract_version` field in `run_manifest.json`, with readers refusing unversioned runs. Today the contract is
  pinned by `tests/test_run_contract.py` and the kit's golden tests instead.
- Dropping the pre-graph ("legacy") manifest shape so every flow emits `topology` / `path_taken`.
- Raising the Python floor from 3.8 to 3.10 (3.8 is still tested in CI).

When a v2.0 item is decided, it moves into the table above in the same PR; when v2.0 ships, this file's status line
changes and each row gets a "removed in" note — the rows are not deleted.
