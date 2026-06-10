# Cross-domain examples — one engine, four domains

Each flow is dependency-free (runs on `python3` alone, in CI) and demonstrates one deterministic gate.
Run any: `python3 ../run.py --flow <name>.json`. Inspect first with `--plan`.

| Flow | Domain | Gate | Stand-in (dep-free) | Swap in for real |
|------|--------|------|---------------------|------------------|
| `fe.json` | Frontend | `cmd_gate` (exit 0) | `python3 --version` | `npm run build` / `eslint .` |
| `be.json` | Backend | `schema_gate` (required fields) | fixed JSON response | `curl` an API → validate the response |
| `db.json` | Database | `recompute_gate` (re-derive total) | fixed rows + total | `psql` query → reconcile counts/sums |
| `ai.json` | AI / LLM | `trace_gate` (every value traces to input) | echo input values | a real LLM call — keep `trace_gate` to block fabrication |

The engine and gates are domain-neutral: each domain plugs in only via its `tool.py` (or a `cmd`) and config — no engine changes. Branching (`branch`/`cases`/`goto`) and `map_over` are covered in `tests/integration/test_branch.py` and `test_map.py`.
