"""Skill A 工具：extract — 從文字輸入抽取讀數（key: value），輸出 readings artifact（含來源追溯）。

數值文法：整數/小數、千分位逗號(1,234)、科學記號(1.2e3)、帶單位(250 mg → 250)。
**不靜默丟資料**：非空非註解(#)行若「含數字卻無法解析成乾淨讀數」→ 記入 `skipped` 且 **fail-loud**
（exit≠0），除非加 `--allow-unparsed`。純文字行（無數字，如 `note: ...`）視為非資料、安靜忽略。
單一工具（python3 stdlib）；路徑由 --in/--out 參數化，無硬編碼。"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import kit  # noqa: E402

DEPS = [{"kind": "python", "min": "3.8"}]
WHO = "extract"
_KV = re.compile(r"^\s*([\w .\-]+?)\s*[:=]\s*(.+?)\s*$")
# 值須「整體」為乾淨數字（可含千分位/科學記號）＋可選尾隨單位；否則視為無法解析（不偷抽中間數字）。
_VAL = re.compile(r"^(-?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*[A-Za-z%µ°/]*$")


def _to_num(v):
    m = _VAL.match((v or "").strip())
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def run(inp, out, allow_unparsed=False):
    readings, trace, skipped = [], [], []
    with open(inp, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            raw = line.rstrip("\n")
            s = raw.strip()
            if not s or s.startswith("#"):
                continue                                  # 空行/註解：非資料，忽略
            kv = _KV.match(raw)
            val = _to_num(kv.group(2)) if kv else None
            if kv and val is not None:
                readings.append({"key": kv.group(1).strip(), "value": val})
                trace.append({"value": kv.group(2).strip(), "source": os.path.basename(inp), "locator": f"line {i}"})
            elif any(c.isdigit() for c in raw):
                skipped.append({"line": i, "text": raw[:100]})   # 含數字卻沒抽出 → 不可靜默丟
            # else：無數字的純文字行 → 非資料，忽略
    kit.write_artifact(kit.artifact("readings@1", WHO, {"readings": readings, "skipped": skipped}, trace), out)
    if skipped and not allow_unparsed:
        det = "\n  - ".join(f"line {x['line']}: {x['text']}" for x in skipped[:8])
        print(f"ERROR: [{WHO}] {len(skipped)} 行含數字卻無法解析為讀數（已記入 skipped、未丟棄）。"
              f"請修正輸入或加 --allow-unparsed：\n  - {det}", file=sys.stderr)
        raise SystemExit(3)
    if skipped:
        print(f"WARNING: [{WHO}] {len(skipped)} 行無法解析（已記入 skipped；--allow-unparsed 放行）", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=WHO)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--allow-unparsed", action="store_true",
                    help="允許含數字卻無法解析的行（記入 skipped、不中止）")
    a = ap.parse_args()
    kit.require_deps(DEPS, who=WHO)
    run(a.inp, a.out, a.allow_unparsed)
    print(f"[{WHO}] OK → {a.out}")


if __name__ == "__main__":
    main()
