# Cross-domain examples — one engine, five shapes

Each flow is dependency-free (runs on `python3` alone, in CI) and demonstrates one deterministic gate
or one topology feature. Run any: `python3 ../run.py --flow <name>.json`.
Inspect first with `--plan` (lists operations **and** statically validates the whole topology),
or draw it with `--graph`.

| Flow | Domain | Gate | Stand-in (dep-free) | Swap in for real |
|------|--------|------|---------------------|------------------|
| `fe.json` | Frontend | `cmd_gate` (exit 0) | `python3 --version` | `npm run build` / `eslint .` |
| `be.json` | Backend | `schema_gate` (required fields) | fixed JSON response | `curl` an API → validate the response |
| `db.json` | Database | `recompute_gate` (re-derive total) | fixed rows + total | `psql` query → reconcile counts/sums |
| `ai.json` | AI / LLM | `trace_gate` (every value traces to input) | echo input values | a real LLM call — keep `trace_gate` to block fabrication |
| `graph.json` | Review loop | `schema_gate` with `schema_ref` (**typed edges**) | `draft` / `verdict` / `accept` | a real drafting step + a real reviewer |

## `graph.json` — the graph-engineering shape

Four nodes with a **bounded back-edge**, the piece a linear pipeline cannot express:

```
draft ──▶ verdict ──▶ gate ──default──▶ accept
  ▲                     │
  └──── reject ─────────┘   back:true, max_revisits=2
```

It exercises, in shipped code, everything the linear examples cannot:

- **Typed edges** — every step declares `schema_ref`, so the handoff contract is checked, not decorative.
- **Unique field ownership** — `draft ← draft`, `verdict ← verdict`; two writers on one field is refused statically.
- **A cycle that is legal because it is bounded** — `max_revisits=2`, enforced in code; the loop
  converges in three rounds (2 defects → 1 → 0 → `pass`).
- **Retry history preserved** — a revisit archives the previous artifact (`draft.visit1.json`, …)
  instead of overwriting it; the manifest's `path_taken[].archived_previous` names each one.
- **Per-edge progress sensing** — identical routing state across revisits is an `idle` stall
  (`lib/loop/progress.py`), which stops the loop *before* the bound when nothing is improving.

The engine and gates stay domain-neutral: each domain plugs in only via its `tool.py` (or a `cmd`)
and config — no engine changes. `map_over` is covered in `tests/integration/test_map.py`.
