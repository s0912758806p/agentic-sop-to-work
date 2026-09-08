# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Static topology analysis: decide whether a flow's graph is legal WITHOUT running it.

Graph Engineering's load-bearing piece. The engine used to enforce one crude rule —
`goto` must be forward-only, so `無迴圈、確定性` (kit/SOP.md). That banned the cycles the
loop instruments in lib/loop/ were built for, leaving exactly one loop in the whole
system: run.py re-running the entire flow. Here the rule becomes "cycles are legal iff
every cycle passes through a declared, bounded back-edge" — determinism unchanged, the
prohibition replaced by a bound.

Five checks, all deterministic, all reported at --plan time (exit 2):

  1. unreachable node   — declared but no path reaches it
  2. read-before-write  — a node reads a field that is not written on EVERY path to it
  3. write conflict     — two nodes declare `writes` on one field (ownership must be unique)
  4. unbounded cycle    — a cycle with no bounded back-edge on it
  5. dangling/ambiguous — a `goto` naming no step, or a duplicate name a `goto` targets

Checks 2 and 3 are the executable form of the audit rule that a shared state with
"無誰給誰什麼的契約" is a FAIL: a unique declaring writer per field plus a guaranteed
write on every path IS the contract. State stays in the artifacts — this module only
reads declarations.

A node's identity is its INDEX, never its name: two steps may legitimately share a name
(the runtime resolves a `goto` to the first match and is otherwise index-driven), so
collapsing nodes by name would invent self-loops that the engine never walks.

Pure stdlib (rung 2/4: networkx would break the machine-enforced stdlib-only invariant).
"""

_ALL = object()  # dataflow "top": every field, before narrowing by intersection


def _node_name(st, i):
    """Display label. Steps may declare neither `id` nor `skill` (a bare cmd step, as in
    the shipped fe.json), so fall back to the index — such a step is still a node."""
    return st.get("id") or st.get("skill") or f"step{i}"


def _kind(st):
    if "branch" in st:
        return "branch"
    if "cmd" in st:
        return "cmd"
    if "tool" in st:
        return "map" if "map_over" in st else "tool"
    return "malformed"


def _case_label(c):
    if c.get("default"):
        return "default"
    w = c.get("when") or {}
    if w.get("op") == "exists":
        return f"exists {w.get('path')}"
    return f"{w.get('path')} {w.get('op')} {w.get('value')!r}"


def build(flow):
    """Return (nodes, edges, name2idx, duplicates).

    Edges mirror the engine's real control flow (run.py): a branch step ALWAYS jumps to a
    case target and never falls through; every other step falls through to the next.
    `to_index` is None for an unresolvable goto — the caller reports it.
    """
    steps = flow.get("steps") or []
    nodes, name2idx, dups = [], {}, []
    for i, st in enumerate(steps):
        name = _node_name(st, i)
        gate_args = (st.get("gate") or {}).get("args") or {}
        nodes.append({"name": name, "index": i, "kind": _kind(st),
                      "reads": list(st.get("reads") or []),
                      "writes": list(st.get("writes") or []),
                      "schema_ref": gate_args.get("schema_ref"),
                      "gate": (st.get("gate") or {}).get("type")})
        if name in name2idx:
            dups.append(name)
        else:
            name2idx[name] = i

    edges = []
    for i, st in enumerate(steps):
        frm = _node_name(st, i)
        if "branch" in st:
            for c in st.get("cases") or []:
                goto = c.get("goto")
                edges.append({"frm": frm, "frm_index": i, "to": goto,
                              "to_index": name2idx.get(goto), "kind": "case",
                              "label": _case_label(c), "back": bool(c.get("back")),
                              "max_revisits": c.get("max_revisits")})
        elif i + 1 < len(steps):
            edges.append({"frm": frm, "frm_index": i, "to": _node_name(steps[i + 1], i + 1),
                          "to_index": i + 1, "kind": "seq", "label": "",
                          "back": False, "max_revisits": None})
    return nodes, edges, name2idx, dups


def _valid_bound(mr):
    """A bound must be a positive int. bool is an int subclass — True is not a bound."""
    return isinstance(mr, int) and not isinstance(mr, bool) and mr >= 1


def _adj(edges):
    adj = {}
    for e in edges:
        adj.setdefault(e["frm_index"], []).append(e["to_index"])
    return adj


def _reachable(nodes, edges):
    """Indices reachable from the entry step (index 0)."""
    if not nodes:
        return set()
    adj = _adj(edges)
    seen, stack = set(), [0]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(t for t in adj.get(n, []) if t not in seen)
    return seen


def _has_cycle(count, edges):
    """DFS cycle detection over indices (colour marking)."""
    adj = _adj(edges)
    WHITE, GREY, BLACK = 0, 1, 2
    colour = [WHITE] * count

    def visit(n):
        colour[n] = GREY
        for t in adj.get(n, []):
            if colour[t] == GREY:
                return True
            if colour[t] == WHITE and visit(t):
                return True
        colour[n] = BLACK
        return False

    return any(colour[n] == WHITE and visit(n) for n in range(count))


def _available(nodes, edges):
    """Must-write dataflow: available[i] = fields written on EVERY path reaching node i.

    Intersection (must) semantics, so uninitialised nodes start at top (_ALL) and narrow.
    The entry node is pinned to the empty set: on the first visit nothing has been written
    yet, even when a back-edge also targets it.
    """
    preds = {n["index"]: [] for n in nodes}
    for e in edges:
        preds[e["to_index"]].append(e["frm_index"])
    writes = {n["index"]: frozenset(n["writes"]) for n in nodes}
    avail = {n["index"]: (frozenset() if n["index"] == 0 else _ALL) for n in nodes}

    for _ in range(len(nodes) + 2):          # monotone narrowing: converges in <= |nodes| passes
        changed = False
        for n in nodes:
            i = n["index"]
            if i == 0:
                continue
            acc = _ALL
            for p in preds[i]:
                pv = avail[p]
                out = _ALL if pv is _ALL else pv | writes[p]
                acc = out if acc is _ALL else (acc if out is _ALL else acc & out)
            if acc is not _ALL and acc != avail[i]:
                avail[i] = acc
                changed = True
        if not changed:
            break
    return avail


def analyze(flow):
    """Return (problems: list[str], info: dict). Empty problems == legal topology.

    `info` carries nodes / edges / owners / reachable for --graph rendering and the run
    manifest's `topology` block, plus `findings` — the same problems with a stable `code`,
    so callers can separate what the pre-graph engine already enforced from what the graph
    model newly checks, without matching on message text.
    """
    nodes, edges, name2idx, dups = build(flow)
    problems, findings = [], []

    def add(code, message):
        problems.append(message)
        findings.append({"code": code, "message": message})

    # A duplicate name only matters when something routes to it — matching the runtime,
    # where name2idx keeps the first match and an untargeted duplicate changes nothing.
    targeted = {e["to"] for e in edges if e["kind"] == "case"}
    for d in sorted(set(dups) & targeted):
        add("duplicate_name",
            f"duplicate step name {d!r}: a goto targets it, so routing is ambiguous")

    for n in nodes:
        if n["kind"] == "malformed":
            add("malformed", f"step {n['name']!r}: malformed — has no 'tool', 'cmd' or 'branch' key")

    live = []
    for e in edges:
        if e["to"] is None:
            add("missing_goto", f"step {e['frm']!r}: a branch case is missing its 'goto'")
        elif e["to_index"] is None:
            add("unknown_goto", f"step {e['frm']!r} goto {e['to']!r}: no such step")
        else:
            live.append(e)

    # Back-edge declarations. A declared bound is what makes a cycle legal, so a lie here
    # (back:true pointing forward) would let a real cycle slip past the DAG check below.
    for e in live:
        if e["kind"] != "case":
            continue
        backward = e["to_index"] <= e["frm_index"]
        if e["back"]:
            if not backward:
                add("back_forward",
                    f"step {e['frm']!r} goto {e['to']!r}: declared back:true but the target is "
                    f"forward — a back-edge must point backward")
            elif not _valid_bound(e["max_revisits"]):
                add("back_unbounded",
                    f"step {e['frm']!r} goto {e['to']!r}: back-edge needs max_revisits as a "
                    f"positive int (got {e['max_revisits']!r}) — an unbounded cycle is refused")
        elif backward:
            add("not_forward_only",
                f"step {e['frm']!r} goto {e['to']!r}: not forward-only — declare back:true "
                f"with max_revisits to make it a bounded back-edge")

    # Every cycle must pass through a *bounded* back-edge: drop those, demand a DAG.
    bounded = {id(e) for e in live
               if e["back"] and _valid_bound(e["max_revisits"])
               and e["to_index"] <= e["frm_index"]}
    if _has_cycle(len(nodes), [e for e in live if id(e) not in bounded]):
        add("unbounded_cycle",
            "unbounded cycle: every cycle must pass through a back-edge declaring "
            "max_revisits — otherwise the loop has no deterministic early stop")

    reach = _reachable(nodes, live)
    for n in nodes:
        if n["index"] not in reach:
            add("unreachable",
                f"unreachable node {n['name']!r}: no path from the entry step reaches it")

    # Field ownership: exactly one declaring writer per field, or the state is a blackboard.
    writers = {}
    for n in nodes:
        for f in n["writes"]:
            writers.setdefault(f, []).append(n["name"])
    for f, ws in sorted(writers.items()):
        if len(ws) > 1:
            add("write_conflict",
                f"write conflict on field {f!r}: declared by {ws} — a field must have exactly "
                f"one writer (unique ownership is what keeps state from becoming a blackboard)")

    # read-before-write, over the reachable subgraph only (an unreachable node's reads are moot).
    if nodes:
        avail = _available(nodes, live)
        for n in nodes:
            if n["index"] not in reach:
                continue
            have = avail[n["index"]]
            have = frozenset() if have is _ALL else have
            for f in n["reads"]:
                if f not in have:
                    owner = writers.get(f)
                    why = (f"written only by {owner[0]!r}, which is not on every path here"
                           if owner else "no node declares writing it")
                    add("read_before_write",
                        f"node {n['name']!r} reads field {f!r} but {why} — "
                        f"the handoff contract has a hole")

    info = {"nodes": nodes, "edges": live, "findings": findings,
            "reachable": sorted(nodes[i]["name"] for i in reach) if nodes else [],
            "owners": {f: ws[0] for f, ws in writers.items() if len(ws) == 1}}
    return problems, info


def _esc(s):
    """Mermaid label escaping: quotes would terminate the label."""
    return str(s).replace('"', "&quot;")


def mermaid(flow, info=None):
    """Deterministic Mermaid flowchart of the topology.

    Back-edges render dotted — they are the retry path, not the forward path. Same flow in,
    same bytes out (no time, no randomness, no dict-order dependence): tests/test_graph_docs.py
    binds the README/SOP.md diagram to this output, so the drawn topology cannot disagree
    with flow.json.
    """
    if info is None:
        _, info = analyze(flow)
    lines = ["flowchart LR"]
    for n in info["nodes"]:
        label = n["name"]
        if n["schema_ref"]:
            label += f"<br/>{n['schema_ref']}"
        shape = ("{{%s}}" % _esc(label)) if n["kind"] == "branch" else ('["%s"]' % _esc(label))
        lines.append(f"    n{n['index']}{shape}")
    for e in info["edges"]:
        label = e["label"]
        if e["back"]:
            bound = f"≤{e['max_revisits']}"
            label = f"{label} ({bound})" if label else bound
        seg = f'|"{_esc(label)}"|' if label else ""
        arrow = "-.->" if e["back"] else "-->"
        lines.append(f"    n{e['frm_index']} {arrow}{seg} n{e['to_index']}")
    return "\n".join(lines)
