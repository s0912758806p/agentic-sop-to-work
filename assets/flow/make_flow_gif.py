#!/usr/bin/env python3
"""Generate assets/flow.gif — an animated, step-by-step conceptual flow for the README.

Same flow as the static Mermaid diagram (Human SOP -> single-tool skills -> run.py
-> per-step gate -> DRAFT -> human approval, with a Stop-hook regression guard), but
revealed one stage at a time with a bilingual caption. Reflects P1 (intake routing:
spec -> as-is / need -> draft SOP -> confirm) and P2 (capped auto fix-loop on a gate
failure: auto-fix & re-run <=3, then stop for a human).

Deterministic: no time/random — same output every run.
Regenerate:  python3 assets/flow/make_flow_gif.py
Dependency:  Pillow (build-time only; NOT part of the stdlib-only kit engine).
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 980, 488
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


F_TITLE = font(22)
F_NODE = font(17)
F_SUB = font(12)
F_CAP = font(20)
F_CAP_ZH = font(18)
F_TAG = font(13)

# themes: (fill, border, text)
DIM = ("#ECEFF1", "#CFD8DC", "#B0BEC5")
NEU = ("#ECEFF1", "#546E7A", "#37474F")
AMBER = ("#FFF8E1", "#F9A825", "#8D6E00")
GREEN = ("#E8F5E9", "#2E7D32", "#1B5E20")
PAPER = ("#FFFDE7", "#C0CA33", "#827717")
RED = ("#FFEBEE", "#C62828", "#B71C1C")
ORANGE = ("#FFF3E0", "#EF6C00", "#E65100")

NW, NHT = 132, 74
XS = [28, 188, 348, 508, 668, 828]   # 6 main-chain columns
MAIN_Y = 104

NODES = {
    "sop":      dict(x=XS[0], y=MAIN_Y, w=NW, h=NHT, label="Human SOP",          theme=NEU),
    "skills":   dict(x=XS[1], y=MAIN_Y, w=NW, h=NHT, label="single-tool\nskills", theme=NEU),
    "run":      dict(x=XS[2], y=MAIN_Y, w=NW, h=NHT, label="run.py",             theme=NEU),
    "gate":     dict(x=XS[3], y=MAIN_Y, w=NW, h=NHT, label="per-step\ngate",     theme=AMBER),
    "draft":    dict(x=XS[4], y=MAIN_Y, w=NW, h=NHT, label="DRAFT",              theme=PAPER),
    "approval": dict(x=XS[5], y=MAIN_Y, w=NW, h=NHT, label="human\napproval",    theme=GREEN),
    "stopfix":  dict(x=XS[3], y=246, w=NW, h=50, label="auto-fix\n· re-run ≤3", theme=ORANGE),
    "reg":      dict(x=XS[1], y=352, w=XS[3] + NW - XS[1], h=46,
                     label="Stop-hook regression gate", theme=RED),
}

# Per-beat narration: (english, chinese). 0..6 reveal + 7 final hold.
CAPS = [
    ("Intake — a spec → use as-is; just a need → Claude drafts an SOP, you confirm.", "意圖分流：有 spec → 照用；只有需求 → Claude 起草 SOP、你確認後再續。"),
    ("Decompose into single-tool skills — one tool, one I/O contract.", "拆成單一工具 skill：一個工具、一份 I/O 契約。"),
    ("run.py orchestrates the steps: sequence · branch · map.", "由 run.py 編排步驟：順序 · 分支 · map。"),
    ("Every step passes a hard gate — cmd · schema · trace · recompute (zero LLM).", "每一步先過硬閘門：cmd · schema · trace · recompute（零 LLM）。"),
    ("Pass → DRAFT.  Fail → auto-fix & re-run (≤3); exhausted → stop for a human.", "通過 → DRAFT；失敗 → 自動修復重跑（≤3），用盡才停下交人；永不假裝過關。"),
    ("A human approves — high-risk calls stay human-owned.", "由人核准——高風險判定永遠由人擁有。"),
    ("Every change re-runs the Stop-hook regression gate.", "每次變更都重跑 Stop-hook 回歸閘門。"),
    ("Intake → skills → gated flow (capped auto-fix) → DRAFT → human approval.", "不臆造、不退化成 mega agent；失敗自動修復有上限。"),
]

ORDER = ["sop", "skills", "run", "gate", "draft", "approval"]
EDGES = [
    ("sop", "skills", "#546E7A", False, 1),
    ("skills", "run", "#546E7A", False, 2),
    ("run", "gate", "#546E7A", False, 3),
    ("gate", "draft", "#2E7D32", False, 4),
    ("gate", "stopfix", "#C62828", False, 4),
    ("stopfix", "run", "#EF6C00", True, 4),   # capped retry loop (P2)
    ("draft", "approval", "#546E7A", False, 5),
    ("reg", "skills", "#C62828", True, 6),
]


def rounded(d, box, fill, border, width=2):
    d.rounded_rectangle(box, radius=12, fill=fill, outline=border, width=width)


def center_text(d, cx, cy, text, fnt, fill):
    lines = text.split("\n")
    bb = d.textbbox((0, 0), "Ag", font=fnt)
    lh = (bb[3] - bb[1]) + 4
    total = lh * len(lines)
    y = cy - total / 2
    for ln in lines:
        w = d.textlength(ln, font=fnt)
        d.text((cx - w / 2, y), ln, font=fnt, fill=fill)
        y += lh


def draw_node(d, nid, level):
    n = NODES[nid]
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    if level == "dim":
        fill, bd, tx = DIM
        bw = 1
    else:
        fill, bd, tx = n["theme"]
        bw = 4 if level == "focus" else 2
    if level == "focus":
        d.rounded_rectangle((x - 5, y - 5, x + w + 5, y + h + 5), radius=14,
                            outline=bd, width=2)
    rounded(d, (x, y, x + w, y + h), fill, bd, bw)
    center_text(d, x + w / 2, y + h / 2, n["label"], F_NODE, tx)


def arrowhead(d, x, y, dx, dy, color, s=8):
    import math
    ang = math.atan2(dy, dx)
    left = (x - s * math.cos(ang) + s * 0.55 * math.cos(ang + 1.5708),
            y - s * math.sin(ang) + s * 0.55 * math.sin(ang + 1.5708))
    right = (x - s * math.cos(ang) - s * 0.55 * math.cos(ang + 1.5708),
             y - s * math.sin(ang) - s * 0.55 * math.sin(ang + 1.5708))
    d.polygon([(x, y), left, right], fill=color)


def edge(d, src, dst, color, dashed):
    a, b = NODES[src], NODES[dst]
    if src == "reg":  # dotted loop back up to skills bottom
        x1, y1 = a["x"] + 60, a["y"]
        x2, y2 = b["x"] + b["w"] / 2, b["y"] + b["h"]
    elif dst == "stopfix":  # gate down to the fix-loop node
        x1, y1 = a["x"] + a["w"] / 2, a["y"] + a["h"]
        x2, y2 = b["x"] + b["w"] / 2, b["y"]
    elif src == "stopfix":  # capped retry loop back up to run.py (P2)
        x1, y1 = a["x"] + a["w"] / 2, a["y"]
        x2, y2 = NODES["run"]["x"] + NODES["run"]["w"] / 2, NODES["run"]["y"] + NODES["run"]["h"]
    else:  # horizontal right->left
        x1, y1 = a["x"] + a["w"], a["y"] + a["h"] / 2
        x2, y2 = b["x"], b["y"] + b["h"] / 2
    if dashed:
        import math
        tot = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(tot // 10))
        for i in range(n):
            if i % 2:
                continue
            t1, t2 = i / n, min((i + 0.6) / n, 1)
            d.line((x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1,
                    x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2), fill=color, width=2)
    else:
        d.line((x1, y1, x2, y2), fill=color, width=3)
    arrowhead(d, x2, y2, x2 - x1, y2 - y1, color)


def render_beat(beat):
    """beat 0..6 = progressive reveal; beat 7 = final hold (all lit)."""
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.text((28, 22), "agentic-sop-kit — how a run flows", font=F_TITLE, fill="#37474F")
    d.line((28, 58, W - 28, 58), fill="#ECEFF1", width=2)

    final = beat >= 7
    focus_idx = beat if not final else len(ORDER)

    for src, dst, color, dashed, rb in EDGES:
        if final or beat >= rb:
            edge(d, src, dst, color, dashed)

    for i, nid in enumerate(ORDER):
        if final:
            lvl = "done"
        elif i < focus_idx:
            lvl = "done"
        elif i == focus_idx:
            lvl = "focus"
        else:
            lvl = "dim"
        draw_node(d, nid, lvl)

    draw_node(d, "stopfix", "done" if (final or beat >= 4) else "dim")
    draw_node(d, "reg", "focus" if beat == 6 else ("done" if (final or beat >= 6) else "dim"))

    # edge tags (P2 fail-path + capped retry loop)
    if final or beat >= 4:
        d.text((XS[3] + NW + 6, MAIN_Y + 4), "pass", font=F_TAG, fill="#2E7D32")
        d.text((XS[3] + NW / 2 + 8, 220), "fail", font=F_TAG, fill="#C62828")
        d.text((XS[2] + NW + 6, 196), "retry ≤3", font=F_TAG, fill="#EF6C00")

    # P1 intake annotation under the Human SOP node
    if beat == 0 or final:
        d.text((XS[0] + 6, MAIN_Y + NHT + 8), "spec → as-is", font=F_TAG, fill="#90A4AE")
        d.text((XS[0] + 6, MAIN_Y + NHT + 24), "need → draft → OK", font=F_TAG, fill="#90A4AE")

    cap_en, cap_zh = CAPS[min(beat, 7)]
    d.rounded_rectangle((28, 410, W - 28, 470), radius=10, fill="#FAFAFA", outline="#ECEFF1", width=2)
    we = d.textlength(cap_en, font=F_CAP)
    d.text(((W - we) / 2, 418), cap_en, font=F_CAP, fill="#263238")
    wz = d.textlength(cap_zh, font=F_CAP_ZH)
    d.text(((W - wz) / 2, 444), cap_zh, font=F_CAP_ZH, fill="#546E7A")
    return img


def main():
    frames = [render_beat(b) for b in range(8)]
    durations = [1400, 1000, 1000, 1100, 1600, 1100, 1100, 1900]
    out = os.path.normpath(OUT)
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=2)
    print(f"wrote {out}  ({len(frames)} frames, {os.path.getsize(out) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
