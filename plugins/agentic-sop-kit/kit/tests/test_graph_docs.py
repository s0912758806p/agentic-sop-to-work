# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""文件不能說謊：把文件裡的拓撲圖與寫死的數字綁到實算值。

專案鐵則：「要保證就別只寫散文——用測試綁住實算值，fail-closed：抓不到宣稱字樣要紅，
不是綠。」改版前這個 repo **一支 docs-freshness 測試都沒有**；這是第一支。

兩層綁定：
  1. 拓撲圖由 `flow.json` 生成，與文件裡的生成區塊**逐位元**比對 → 圖不可能與流程不一致。
  2. 文件裡寫死的閘門數與閘門名稱綁到 `gates.REGISTRY`（真物件）。
     檢查種類的**數字**刻意不綁——唯一辦法是切 `graph.py` 的原始碼字串，
     那種聰明的綁法比沒綁更危險（改個 code 名數字不變、註解裡出現 `add("` 就誤計）。
     文件保留檢查**清單**，數字不寫。

**fail-closed 是重點**：抓不到生成區塊標記時必須紅。若寫成「找不到就跳過」，
刪掉標記就能讓測試變綠——那樣的測試比沒有更危險。

可攜性邊界：kit 自帶的文件（SOP.md / README.md / workflow/examples/README.md）永遠隨 kit
一起被複製，所以硬綁；repo 根目錄的 README.md 在 kit 的可攜邊界之外，只有在偵測到自己
就在原始 repo（存在 .claude-plugin/marketplace.json）時才要求，否則不適用。
"""
import os
import subprocess
import sys
import unittest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KIT, "lib"))
import gates  # noqa: E402
import graph  # noqa: E402

RUN = os.path.join(KIT, "workflow", "run.py")
GRAPH_FLOW = os.path.join(KIT, "workflow", "examples", "graph.json")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(KIT)))

BEGIN = "<!-- BEGIN GENERATED: topology -->"
END = "<!-- END GENERATED: topology -->"

# Docs that always travel with the kit -> bound unconditionally.
KIT_DOCS = [os.path.join(KIT, "SOP.md"), os.path.join(KIT, "README.md")]


def _in_source_repo():
    return os.path.exists(os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json"))


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def extract_block(text, begin=BEGIN, end=END):
    """Return the text between the markers, or None when either marker is absent.

    Returning None (rather than "") is what lets the caller fail closed: a missing marker
    is a failure, never a silent pass.
    """
    if begin not in text or end not in text:
        return None
    body = text.split(begin, 1)[1].split(end, 1)[0]
    return body.strip("\n")


def expected_block():
    """The topology block exactly as the docs must carry it: a mermaid fence around the
    engine's own rendering of the shipped graph example."""
    import json
    with open(GRAPH_FLOW, encoding="utf-8") as f:
        flow = json.load(f)
    return "```mermaid\n" + graph.mermaid(flow) + "\n```"


class GeneratedTopologyMatchesTheFlow(unittest.TestCase):
    def test_kit_docs_carry_the_generated_block(self):
        for path in KIT_DOCS:
            with self.subTest(doc=os.path.relpath(path, KIT)):
                block = extract_block(_read(path))
                self.assertIsNotNone(
                    block,
                    f"{os.path.relpath(path, KIT)} 缺少生成區塊標記 {BEGIN} … {END}；"
                    f"標記不見了必須紅（fail-closed），不得靜默通過")
                self.assertEqual(
                    block, expected_block(),
                    f"{os.path.relpath(path, KIT)} 的拓撲圖與 workflow/examples/graph.json 不一致；"
                    f"用 `python3 workflow/run.py --flow workflow/examples/graph.json --graph` 重新產生")

    def test_repo_readme_carries_the_generated_block(self):
        if not _in_source_repo():
            raise unittest.SkipTest("kit 被複製到別的專案，repo README 不在可攜邊界內")
        path = os.path.join(REPO_ROOT, "README.md")
        block = extract_block(_read(path))
        self.assertIsNotNone(block, f"README.md 缺少生成區塊標記；fail-closed 必須紅")
        self.assertEqual(block, expected_block(), "README.md 的拓撲圖與 graph.json 不一致")

    def test_cli_output_is_what_the_docs_claim(self):
        """文件教人用 --graph 重新產生；那條命令的輸出必須真的等於文件裡的圖。"""
        r = subprocess.run([sys.executable, RUN, "--flow", GRAPH_FLOW, "--graph"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual("```mermaid\n" + r.stdout.strip("\n") + "\n```", expected_block())


class HardcodedNumbersAreBoundToRealValues(unittest.TestCase):
    """文件裡寫死的數字綁實算值——加了 gate 卻忘了改文件就會紅。"""

    def test_gate_count_claim_matches_the_registry(self):
        n = len(gates.REGISTRY)
        claim = f"{n} deterministic gates"
        found = [os.path.relpath(p, KIT) for p in KIT_DOCS if claim in _read(p)]
        self.assertTrue(found,
                        f"kit 文件中找不到宣稱字樣 {claim!r}（實際 gate 數 ={n}）。"
                        f"抓不到宣稱字樣要紅：文件要嘛寫錯數字，要嘛把這句話刪了")

    def test_every_gate_is_named_in_the_kit_docs(self):
        docs = "\n".join(_read(p) for p in KIT_DOCS)
        for name in sorted(gates.REGISTRY):
            with self.subTest(gate=name):
                self.assertIn(name, docs, f"gate {name} 未出現在 kit 文件中")


class FailClosedIsRealNotDecorative(unittest.TestCase):
    """後設測試：證明「標記不見了會紅」不是願望。"""

    def test_extractor_returns_none_when_markers_are_missing(self):
        self.assertIsNone(extract_block("# a doc with no generated block\n"))

    def test_extractor_returns_none_when_only_the_begin_marker_is_present(self):
        self.assertIsNone(extract_block(f"{BEGIN}\nhalf a block\n"))

    def test_extractor_reads_the_block_when_both_markers_are_present(self):
        self.assertEqual(extract_block(f"x\n{BEGIN}\nbody\n{END}\ny"), "body")



if __name__ == "__main__":
    unittest.main(verbosity=2)
