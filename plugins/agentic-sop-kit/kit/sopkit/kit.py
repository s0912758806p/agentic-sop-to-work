# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Agentic-SOP kit — 可攜核心（無任何硬編碼專案路徑）。

設計原則（對應任務 1 驗收）：
  • 路徑一律相對 kit 根解析（`config.kit_root()`，呼叫時才讀 `SOPKIT_ROOT`），或由呼叫端以參數傳入 → 複製到任何專案皆可跑。
  • 依賴**完整宣告 + 缺項明確報錯**（`require_deps` 拋 `MissingDeps`，絕不靜默失敗）。
  • skill 間以 **JSON artifact** 交接，介面固定（schema / produced_by / data / trace）。
  • 純標準庫，無第三方相依 → 空白專案 `python3` 即可執行範例。
"""
import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime

from . import config
from .console import safe_print


def __getattr__(name):
    # KIT_ROOT stays readable for v1.10 callers, but is computed on access (SOPKIT_ROOT is
    # no longer frozen at import time).
    if name == "KIT_ROOT":
        return config.kit_root()
    raise AttributeError(name)


def kit_path(*parts):
    return os.path.join(config.kit_root(), *parts)


# 執行期狀態＝每個部署自己的回歸快照/重試計數/回歸紀錄/健康基線。複製 kit（bootstrap 導入、
# 測試用拋棄式複本）時一律排除：帶過去的快照會讓目標的第一次 verify 判成「無變更」而略過全部測試。
RUNTIME_STATE = (".verify_state.json", ".retry_count", "regression_log.jsonl", ".health_baseline.json")
COPY_EXCLUDE = ("runs", "__pycache__", "*.pyc", ".DS_Store", ".git", ".pytest_cache",
                "*.egg-info") + RUNTIME_STATE


def copy_kit(src, dst):
    """把 kit 從 src 複製到 dst，排除執行期狀態與雜項（唯一的複製規則來源）。"""
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*COPY_EXCLUDE))


class MissingDeps(Exception):
    """缺依賴 → 明確報錯（非靜默失敗）。"""


def check_deps(deps):
    """deps: list[dict]。kind ∈ {python, module, env, exe}。回傳缺項清單（str）。"""
    missing = []
    for d in deps:
        k = d.get("kind")
        if k == "python":
            need = tuple(int(x) for x in str(d["min"]).split("."))
            if tuple(sys.version_info[:len(need)]) < need:
                have = ".".join(map(str, sys.version_info[:len(need)]))
                missing.append(f"python>={d['min']}（目前 {have}）")
        elif k == "module":
            try:
                __import__(d["name"])
            except Exception:
                missing.append(f"python 模組 '{d['name']}'" + (f"（{d.get('hint')}）" if d.get("hint") else ""))
        elif k == "env":
            if not os.environ.get(d["name"]):
                missing.append(f"環境變數 '{d['name']}'" + (f"（{d.get('hint')}）" if d.get("hint") else ""))
        elif k == "exe":
            if shutil.which(d["name"]) is None:
                missing.append(f"可執行檔 '{d['name']}'" + (f"（{d.get('hint')}）" if d.get("hint") else ""))
        else:
            missing.append(f"未知依賴種類: {k!r}")
    return missing


def require_deps(deps, who="this skill"):
    """缺任一依賴 → 拋 MissingDeps（列出全部缺項）；絕不靜默繼續。"""
    missing = check_deps(deps)
    if missing:
        raise MissingDeps(f"[{who}] 缺少依賴，請先安裝/設定：\n  - " + "\n  - ".join(missing))


def read_artifact(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_artifact(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def artifact(schema, produced_by, data, trace=None):
    """skill 交接用的標準 artifact 結構。trace = 來源追溯（可選）。"""
    return {"schema": schema, "produced_by": produced_by, "data": data, "trace": trace or []}


def run_dir(base=None, run_id=None):
    """run-scoped 輸出目錄（預設 config.runs_base()/<run_id>；不覆蓋既有產物）。"""
    base = base or config.runs_base()[0]
    # 加隨機後綴避免同微秒平行執行碰撞（run-scoped 隔離）。
    run_id = run_id or (datetime.now().strftime("run_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8])
    d = os.path.join(base, run_id)
    os.makedirs(d, exist_ok=True)
    return d


def skill_main(deps, who, fn):
    """skill tool.py 共用進入點：宣告依賴→缺則報錯→解析 --in/--out→執行 fn(inp, out)。"""
    ap = argparse.ArgumentParser(description=who)
    ap.add_argument("--in", dest="inp", required=True, help="上游 artifact / 輸入檔")
    ap.add_argument("--out", dest="out", required=True, help="本 skill 輸出 artifact")
    a = ap.parse_args()
    require_deps(deps, who=who)          # 缺依賴 → 明確報錯（exit !=0），非靜默
    fn(a.inp, a.out)
    safe_print(f"[{who}] OK → {a.out}")
