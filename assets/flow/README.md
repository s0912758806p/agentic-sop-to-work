# README flow animation

`../flow.gif` (the animated diagram in the project README) is **generated** by
`make_flow_gif.py` — it is not hand-drawn, so it stays in sync with the flow.

Regenerate after changing the flow, then commit the updated `flow.gif`:

```
python3 assets/flow/make_flow_gif.py
```

- **Deterministic** — no time/random, identical output every run.
- **Pillow** is a *build-time* dependency only (`pip install pillow`); it is **not**
  used by the kit engine, which stays stdlib-only.
- Edit the `NODES`, `EDGES`, and `CAPS` tables at the top of the script to change
  the diagram or the per-step captions.
