# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""new_skill.py — 依拆解規則 scaffold 一支新的「單一工具 skill」。

從 templates/skill_template/ 複製出 skills/<name>/（去 .tmpl、替換 <skill-name>），
建立 tests/unit/test_<name>.py 骨架，並登記到 tests/registry.json。
之後請填 DEPS / I-O / run()，把該步加進 workflow/flow.json；完成並通過後，
用 export_claude_skill.py 產出對話可觸發的 runner skill。

用法: python3 agentic-sop-kit/new_skill.py --name <name> [--force]
"""
import argparse
import json
import os
import re


def _root():
    return os.environ.get("SOPKIT_ROOT") or os.path.dirname(os.path.abspath(__file__))


_TEST_STUB = '''# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
"""Unit test 骨架 for skill '{name}' — 請補上真正的行為測試（餵固定輸入、檢查輸出 artifact）。"""
import importlib.util
import os
import unittest

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "skills", "{name}", "tool.py")


def _load():
    spec = importlib.util.spec_from_file_location("{name}_tool", TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Test{cls}(unittest.TestCase):
    def test_contract(self):
        m = _load()
        self.assertEqual(m.WHO, "{name}")
        self.assertIsInstance(m.DEPS, list)
        # TODO: 餵固定輸入呼叫 m.run(inp, out)，檢查輸出 artifact 正確、缺值標【待補】不臆造。


if __name__ == "__main__":
    unittest.main()
'''


def _cls(name):
    return "".join(p.capitalize() for p in re.split(r"[^0-9A-Za-z]+", name) if p) or "Skill"


def create(name, force=False, root=None):
    """Scaffold skills/<name>/ + 測試骨架 + 登記 registry。回傳新 skill 目錄。"""
    root = root or _root()
    if not re.match(r"^[A-Za-z][\w-]*$", name):
        raise SystemExit(f"❌ 不合法的 skill 名稱：{name!r}（字母開頭，可含字母/數字/_/-）")
    skill_dir = os.path.join(root, "skills", name)
    if os.path.exists(skill_dir) and not force:
        raise SystemExit(f"❌ 已存在 {skill_dir}（要覆蓋加 --force）")
    tpl = os.path.join(root, "templates", "skill_template")
    os.makedirs(skill_dir, exist_ok=True)
    for tmpl, out in (("SKILL.md.tmpl", "SKILL.md"), ("tool.py.tmpl", "tool.py")):
        body = open(os.path.join(tpl, tmpl), encoding="utf-8").read().replace("<skill-name>", name)
        open(os.path.join(skill_dir, out), "w", encoding="utf-8").write(body)
    test_rel = f"tests/unit/test_{name}.py"
    os.makedirs(os.path.join(root, "tests", "unit"), exist_ok=True)
    open(os.path.join(root, test_rel), "w", encoding="utf-8").write(
        _TEST_STUB.format(name=name, cls=_cls(name)))
    reg_path = os.path.join(root, "tests", "registry.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    reg.setdefault("skills", {})[name] = {"dir": f"skills/{name}", "tests": [test_rel]}
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ 建立 skills/{name}/（SKILL.md + tool.py）")
    print(f"✅ 建立 {test_rel}（骨架）並登記 tests/registry.json")
    print("下一步：① 填 DEPS / I-O / run()；② 把該步加進 workflow/flow.json；"
          f"③ 完成並通過後：python3 export_claude_skill.py --skill {name} --project .")
    return skill_dir


def main(argv=None):
    ap = argparse.ArgumentParser(description="scaffold a new single-tool skill")
    ap.add_argument("--name", required=True, help="新 skill 名稱（= 它綁定的單一工具）")
    ap.add_argument("--force", action="store_true", help="覆蓋既有 skills/<name>/")
    a = ap.parse_args(argv)
    create(a.name, a.force)


if __name__ == "__main__":
    main()
