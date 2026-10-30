#!/usr/bin/env python3
"""Generate assets/flow.gif — the README's animated *signal flow*.

A signal (a moving dot) travels the edges one beat at a time, with a bilingual plain-language
caption. Colour says what happened to it:
  green  = passed          red    = blocked / refused
  orange = bounded retry or send-back (always capped)
  purple = handed to review (second-opinion-honesty · alcoa-guard)

What each beat claims, and where the code that makes it true lives:
  0  SOP / need -> --plan                 workflow/run.py --plan · sopkit/graph.analyze
  1  illegal topology -> refused (exit 2)  sopkit/graph.py (unreachable, unbounded cycle, ...)
  2  run.py -> step check                  sopkit/runner.py: a step fails if its tool fails or
                                           writes no output; an attached gate (5 kinds,
                                           sopkit/gates.py, zero LLM) verifies the output
  3  fail -> auto-fix -> re-run            --max-fix-retries budget + stall (sopkit/loop/progress)
  4  bounded back-edge                     back:true + max_revisits (sopkit/graph.valid_bound)
  5  DRAFT -> review                       companions read the run dir via shared/sopcore/run_contract
  6  human sign-off                        outputs are DRAFTs; the human owns the verdict
  7  change -> Stop-hook regression        hooks/stop_gate.py -> kit/tests/verify.py
It is hand-maintained (nothing binds it to the engine) — keep the table above honest when
editing NODES / EDGES / BEATS.

Deterministic: no time/random — same output every run.
Regenerate:  uv run --with pillow python3 assets/flow/make_flow_gif.py
Dependency:  Pillow (build-time only; NOT part of the stdlib-only plugins).
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 980, 520
OUT = os.path.join(os.path.dirname(__file__), os.pardir, "flow.gif")

FONT_CANDIDATES = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


F_TITLE, F_NODE, F_SUB, F_TAG, F_CAP, F_CAP_ZH = (font(s) for s in (21, 16, 13, 12, 19, 17))

# signal colours
GREEN, RED, ORANGE, PURPLE, GREY = "#2E7D32", "#C62828", "#EF6C00", "#6A1B9A", "#546E7A"
# node themes: (fill, border, text)
DIM = ("#F5F7F8", "#DDE3E6", "#B0BEC5")
THEME = {
    "neu": ("#ECEFF1", "#546E7A", "#263238"),
    "amber": ("#FFF8E1", "#F9A825", "#6D5300"),
    "paper": ("#FFFDE7", "#C0CA33", "#5F6300"),
    "purple": ("#F3E5F5", "#6A1B9A", "#4A148C"),
    "green": ("#E8F5E9", "#2E7D32", "#1B5E20"),
    "red": ("#FFEBEE", "#C62828", "#B71C1C"),
    "orange": ("#FFF3E0", "#EF6C00", "#E65100"),
}

NW, NH, TOP = 118, 66, 112
COL = [20 + i * 136 for i in range(7)]


def node(col, y, label, sub, theme, w=NW, h=NH, x=None):
    return dict(x=COL[col] if x is None else x, y=y, w=w, h=h, label=label, sub=sub, theme=theme)


NODES = {
    "in": node(0, TOP, "SOP / need", "SOP／需求", "neu"),
    "plan": node(1, TOP, "--plan", "先檢查流程", "neu"),
    "run": node(2, TOP, "run.py", "程式逐步執行", "neu"),
    "gate": node(3, TOP, "check", "檢查／閘門", "amber"),
    "draft": node(4, TOP, "DRAFT", "只是草稿", "paper"),
    "review": node(5, TOP, "review", "誠實・ALCOA+", "purple"),
    "human": node(6, TOP, "human", "人核准", "green"),
    "refuse": node(1, 262, "exit 2", "拒絕開跑", "red", h=52),
    "fix": node(3, 262, "auto-fix", "修復・有上限", "orange", h=52),
    "reg": node(0, 360, "Stop hook: change → tests → block", "回歸閘門：改程式就重跑測試",
                "red", w=COL[3] + NW - COL[0], h=50),
}


def _c(n):  # centre
    return n["x"] + n["w"] / 2, n["y"] + n["h"] / 2


def _r(n):
    return n["x"] + n["w"], n["y"] + n["h"] / 2


def _l(n):
    return n["x"], n["y"] + n["h"] / 2


def _poly(name):
    N = NODES
    if name in ("in>plan", "plan>run", "run>gate", "gate>draft", "draft>review", "review>human"):
        a, b = name.split(">")
        return [_r(N[a]), _l(N[b])]
    p, r, g, f, rg = N["plan"], N["run"], N["gate"], N["fix"], N["reg"]
    if name == "plan>refuse":
        return [(_c(p)[0], p["y"] + p["h"]), (_c(p)[0], N["refuse"]["y"])]
    if name == "gate>fix":
        return [(_c(g)[0], g["y"] + g["h"]), (_c(g)[0], f["y"])]
    if name == "fix>run":
        x = r["x"] + r["w"] - 26
        return [_l(f), (x, _c(f)[1]), (x, r["y"] + r["h"])]
    if name == "gate>run(back)":
        y = TOP - 30
        return [(_c(g)[0], g["y"]), (_c(g)[0], y), (_c(r)[0], y), (_c(r)[0], r["y"])]
    if name == "reg>run":
        x = r["x"] + 26
        return [(x, rg["y"]), (x, r["y"] + r["h"])]
    raise KeyError(name)


# (edge, colour, dashed, tag, tag position offset)
EDGES = {
    "in>plan": (GREY, False, None),
    "plan>run": (GREEN, False, None),
    "plan>refuse": (RED, False, "illegal"),
    "run>gate": (GREY, False, None),
    "gate>fix": (RED, False, "fail"),
    "fix>run": (ORANGE, True, "retry ≤N"),
    "gate>run(back)": (ORANGE, True, "send back ≤N"),
    "gate>draft": (GREEN, False, None),
    "draft>review": (PURPLE, False, None),
    "review>human": (GREEN, False, None),
    "reg>run": (RED, True, None),
}

# beat: (edges revealed this beat, signal path [(edge, colour)], nodes revealed, caption EN, caption ZH)
BEATS = [
    (["in>plan"], [("in>plan", GREEN)], ["in", "plan"],
     "You bring an SOP or a need. First the flow itself is checked.",
     "你給 SOP 或需求；先檢查流程本身合不合法。"),
    (["plan>refuse"], [("plan>refuse", RED)], ["refuse"],
     "A dead end or an endless loop? Refused before anything runs.",
     "流程有死路或無限迴圈？還沒開跑就拒絕。"),
    (["plan>run", "run>gate"], [("plan>run", GREEN), ("run>gate", GREEN)], ["run", "gate"],
     "Code runs each step. A failed step stops; gates check the output — no AI grading itself.",
     "每一步由程式執行，失敗就停；閘門驗產出——不讓 AI 自己打分數。"),
    (["gate>fix", "fix>run"], [("gate>fix", RED), ("fix>run", ORANGE)], ["fix"],
     "Failed? Auto-fix and re-run — capped, and it stops if it is going in circles.",
     "沒過？自動修、重跑；次數有上限，原地打轉就停。"),
    (["gate>run(back)"], [("gate>run(back)", ORANGE)], [],
     "A reviewer step can send work back — only a declared number of times.",
     "審查可以退件重做，但退回次數有上限。"),
    (["gate>draft", "draft>review"], [("gate>draft", GREEN), ("draft>review", PURPLE)], ["draft", "review"],
     "The result is only a DRAFT, then checked for honesty and data integrity.",
     "產出永遠只是草稿，再做誠實審查與資料完整性檢查。"),
    (["review>human"], [("review>human", GREEN)], ["human"],
     "A human signs off. High-risk calls stay with people.",
     "最後由人核准；高風險判斷永遠是人的。"),
    (["reg>run"], [("reg>run", RED)], ["reg"],
     "Changed the code? Regression tests run automatically; a break blocks.",
     "改了程式？回歸測試自動跑，壞了就擋下。"),
]
FINAL = ("Never invents facts · never runs away · a human owns the result.",
         "不臆造 · 不失控 · 人負責。")

TRAVEL = 9          # frames per edge the signal travels
TRAVEL_MS = 55
HOLD_MS = 1500
FINAL_MS = 2600


# ---------------------------------------------------------------- drawing
def center_text(d, cx, cy, lines):
    hs = [d.textbbox((0, 0), t, font=f)[3] + 3 for t, f, _ in lines]
    y = cy - sum(hs) / 2
    for (t, f, c), h in zip(lines, hs):
        d.text((cx - d.textlength(t, font=f) / 2, y), t, font=f, fill=c)
        y += h


def draw_node(d, nid, level):
    n = NODES[nid]
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    fill, bd, tx = DIM if level == "dim" else THEME[n["theme"]]
    if level == "focus":
        d.rounded_rectangle((x - 5, y - 5, x + w + 5, y + h + 5), radius=14, outline=bd, width=2)
    d.rounded_rectangle((x, y, x + w, y + h), radius=11, fill=fill, outline=bd,
                        width=3 if level == "focus" else (1 if level == "dim" else 2))
    sub_c = tx if level == "dim" else "#546E7A"
    center_text(d, x + w / 2, y + h / 2, [(n["label"], F_NODE, tx), (n["sub"], F_SUB, sub_c)])


def _seglen(pts):
    return [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]


def point_at(pts, t):
    segs = _seglen(pts)
    dist = t * sum(segs)
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if dist <= L or L == segs[-1]:
            k = 0 if L == 0 else min(dist / L, 1)
            return a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
        dist -= L
    return pts[-1]


def arrowhead(d, a, b, color, s=9):
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    l = (b[0] - s * math.cos(ang) + s * .55 * math.cos(ang + 1.5708),
         b[1] - s * math.sin(ang) + s * .55 * math.sin(ang + 1.5708))
    r = (b[0] - s * math.cos(ang) - s * .55 * math.cos(ang + 1.5708),
         b[1] - s * math.sin(ang) - s * .55 * math.sin(ang + 1.5708))
    d.polygon([b, l, r], fill=color)


def draw_edge(d, name, lit):
    color, dashed, tag = EDGES[name]
    c = color if lit else "#DDE3E6"
    pts = _poly(name)
    for a, b in zip(pts, pts[1:]):
        if dashed:
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            n = max(1, int(L // 9))
            for i in range(0, n, 2):
                t1, t2 = i / n, min((i + 1) / n, 1)
                d.line((a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1,
                        a[0] + (b[0] - a[0]) * t2, a[1] + (b[1] - a[1]) * t2), fill=c, width=2)
        else:
            d.line((*a, *b), fill=c, width=3)
    arrowhead(d, pts[-2], pts[-1], c)
    if tag and lit:
        a, b = pts[-2], pts[-1]   # the last segment carries the tag
        tw = d.textlength(tag, font=F_TAG)
        if name == "gate>run(back)":
            pos = ((pts[1][0] + pts[2][0]) / 2 - tw / 2, pts[1][1] - 17)
        elif name == "fix>run":   # left of the vertical line, clear of the boxes
            pos = (a[0] - tw - 7, (a[1] + b[1]) / 2 - 7)
        else:  # vertical edges going down
            pos = (a[0] + 7, (a[1] + b[1]) / 2 - 7)
        d.text(pos, tag, font=F_TAG, fill=color)


def draw_signal(d, name, color, t):
    x, y = point_at(_poly(name), t)
    d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=_halo(color))
    d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline="#FFFFFF", width=2)


def _halo(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(int(v + (255 - v) * .72) for v in (r, g, b))


def legend(d):
    x = W - 20
    for label, c in reversed([("pass 通過", GREEN), ("blocked 擋下", RED),
                              ("bounded retry 有上限重試", ORANGE), ("review 審查", PURPLE)]):
        w = d.textlength(label, font=F_TAG)
        x -= w
        d.text((x, 26), label, font=F_TAG, fill="#455A64")
        x -= 16
        d.ellipse((x, 28, x + 10, 38), fill=c)
        x -= 16


def frame(lit_edges, lit_nodes, focus, caption, signal=None):
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.text((20, 20), "agentic-sop-to-work — signal flow ｜ 訊號流程", font=F_TITLE, fill="#263238")
    legend(d)
    d.line((20, 56, W - 20, 56), fill="#ECEFF1", width=2)
    for e in EDGES:
        draw_edge(d, e, e in lit_edges)
    for nid in NODES:
        lvl = "focus" if nid in focus else ("done" if nid in lit_nodes else "dim")
        draw_node(d, nid, lvl)
    if signal:
        draw_signal(d, *signal)
    en, zh = caption
    d.rounded_rectangle((20, 438, W - 20, 502), radius=10, fill="#FAFAFA", outline="#ECEFF1", width=2)
    d.text(((W - d.textlength(en, font=F_CAP)) / 2, 446), en, font=F_CAP, fill="#263238")
    d.text(((W - d.textlength(zh, font=F_CAP_ZH)) / 2, 473), zh, font=F_CAP_ZH, fill="#546E7A")
    return img


def build():
    frames, durations = [], []
    lit_e, lit_n = set(), set()
    for new_e, path, new_n, en, zh in BEATS:
        lit_e |= set(new_e)
        for name, color in path:
            for i in range(TRAVEL + 1):
                frames.append(frame(lit_e, lit_n, set(new_n), (en, zh), (name, color, i / TRAVEL)))
                durations.append(TRAVEL_MS)
        lit_n |= set(new_n)
        frames.append(frame(lit_e, lit_n, set(new_n), (en, zh)))
        durations.append(HOLD_MS)
    frames.append(frame(lit_e, lit_n, set(), FINAL))
    durations.append(FINAL_MS)
    return frames, durations


def main():
    frames, durations = build()
    pal = frames[-1].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    out = os.path.normpath(OUT)
    q[0].save(out, save_all=True, append_images=q[1:], duration=durations, loop=0,
              optimize=True, disposal=1)
    print(f"wrote {out}  ({len(q)} frames, {os.path.getsize(out) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
