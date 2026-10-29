# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Unit tests for the shared core (`shared/sopcore/`), the single source vendored into each
companion plugin as `<pkg>/_core/` by tools/sync_core.py.

Run: python3 tests/test_sopcore.py
"""
import json
import os
import sys
import tempfile
import unittest
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared"))
from sopcore import arithmetic, cli, findings, markers, report, run_contract, vendor  # noqa: E402


class TestArithmetic(unittest.TestCase):
    def test_empty_list_fails_for_every_numeric_op(self):
        for op in ("sum", "mean", "min", "max"):
            ok, derived, reason = arithmetic.recompute(op, [], 0)
            self.assertFalse(ok, op)
            self.assertIsNone(derived, op)
            self.assertIn("no items", reason)

    def test_empty_count_is_zero(self):
        self.assertEqual(arithmetic.recompute("count", [], 0)[:2], (True, 0))

    def test_sum_uses_fsum(self):
        # sum() gives 0.9999999999999999 here; fsum gives exactly 1.0.
        ok, derived, _ = arithmetic.recompute("sum", [0.1] * 10, 1.0)
        self.assertTrue(ok)
        self.assertEqual(derived, 1.0)

    def test_mismatch_reason_names_recomputed_and_stated(self):
        ok, derived, reason = arithmetic.recompute("sum", [1, 2, 3], 7)
        self.assertFalse(ok)
        self.assertEqual(derived, 6.0)
        self.assertIn("recomputed sum=6.0 vs stated 7", reason)

    def test_count_is_exact_not_truncated(self):
        self.assertFalse(arithmetic.recompute("count", [1, 2, 3], 3.7)[0])
        self.assertTrue(arithmetic.recompute("count", [1, 2, 3], "3")[0])

    def test_unknown_op_and_bad_inputs_never_raise(self):
        self.assertIn("unknown op", arithmetic.recompute("median", [1, 2], 1.5)[2])
        self.assertIn("non-numeric", arithmetic.recompute("sum", [1, "x"], 1)[2])
        self.assertIn("not numeric", arithmetic.recompute("sum", [1, 2], "abc")[2])
        self.assertIn("not a list", arithmetic.recompute("sum", "vals", 1)[2])

    def test_reeval_verdict(self):
        self.assertEqual(arithmetic.reeval_verdict(96.5, 98.0, 102.0, "pass")[:2], (False, "fail"))
        self.assertEqual(arithmetic.reeval_verdict(99.0, 98.0, None, "pass")[:2], (True, "pass"))


class TestMarkers(unittest.TestCase):
    def test_tbd_constant_and_predicates(self):
        self.assertEqual(markers.TBD, "【待補】")
        self.assertTrue(markers.is_tbd(" 【待補】 "))
        self.assertFalse(markers.is_tbd("lot 【待補】"))
        self.assertTrue(markers.contains_tbd("lot 【待補】"))
        self.assertFalse(markers.is_tbd(None))
        self.assertFalse(markers.contains_tbd(None))


@dataclass
class _F:
    id: str
    severity: str


class TestFindings(unittest.TestCase):
    def test_dedupe_keeps_first_and_order(self):
        fs = [_F("a", "HARD"), _F("b", "SOFT"), _F("a", "SOFT")]
        out = findings.dedupe(fs)
        self.assertEqual([(f.id, f.severity) for f in out], [("a", "HARD"), ("b", "SOFT")])

    def test_dedupe_custom_key_and_count(self):
        fs = [_F("a", "HARD"), _F("a", "HARD")]
        self.assertEqual(len(findings.dedupe(fs, key=lambda f: id(f))), 2)
        self.assertEqual(findings.count(fs), (2, 0))
        self.assertEqual(findings.Severity.HARD, "HARD")

    def test_finding_base(self):
        f = findings.Finding(id="x", severity=findings.Severity.SOFT, location="l", detail="d")
        self.assertEqual(findings.count([f]), (0, 1))


class TestReport(unittest.TestCase):
    def test_frame_is_frozen_advisory(self):
        self.assertEqual(report.frame(), {"verdict": "ADVISORY_ONLY", "human_owns_verdict": True})

    def test_write_dual_checks_frame(self):
        with tempfile.TemporaryDirectory() as d:
            rep = {"schema": "x@1", **report.frame()}
            j, m = report.write_dual(rep, os.path.join(d, "o"), "x", lambda r: "# x\n")
            with open(j, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["verdict"], "ADVISORY_ONLY")
            with open(m, encoding="utf-8") as f:
                self.assertEqual(f.read(), "# x\n")
            with self.assertRaises(ValueError):
                report.write_dual({"verdict": "APPROVED"}, d, "y", lambda r: "")
            # a non-advisory tool (a lint gate) opts out of the frame check
            report.write_dual({"clean": True}, d, "z", lambda r: "", advisory=False)


class TestCli(unittest.TestCase):
    def test_skeleton_args(self):
        import argparse
        ap = argparse.ArgumentParser()
        cli.add_run_args(ap, out_base_help="out")
        a = ap.parse_args(["--run-dir", "r", "--out-base", "o"])
        self.assertEqual((a.run_dir, a.out_base), ("r", "o"))

    def test_default_out_base_is_cwd_relative(self):
        self.assertEqual(cli.default_out_base(".x-runs"), os.path.join(os.getcwd(), ".x-runs"))


class TestVendorStamp(unittest.TestCase):
    def test_round_trip_and_edit_detection(self):
        body = "# SPDX\nx = 1\n"
        s = vendor.stamp(body, "shared/sopcore/m.py")
        self.assertTrue(s.startswith(vendor.MARK))
        self.assertEqual(vendor.unstamp(s), (body, vendor.digest(body)))
        self.assertTrue(vendor.intact(s))
        self.assertTrue(vendor.intact(s.replace("\n", "\r\n")))   # CRLF checkout is not drift
        self.assertFalse(vendor.intact(s.replace("x = 1", "x = 2")))
        self.assertIsNone(vendor.intact(body))

    def test_shebang_stays_first(self):
        s = vendor.stamp("#!/usr/bin/env python3\nprint(1)\n", "src")
        self.assertTrue(s.startswith("#!/usr/bin/env python3\n" + vendor.MARK))
        self.assertTrue(vendor.intact(s))


class TestSyncCore(unittest.TestCase):
    def test_check_detects_missing_edited_and_stale(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import sync_core
        real_root = sync_core.ROOT
        with tempfile.TemporaryDirectory() as d:
            try:
                sync_core.ROOT = d
                for plugin in sync_core.COMPANIONS:
                    os.makedirs(os.path.join(d, "plugins", plugin))
                self.assertTrue(any(p.startswith("missing") for p in sync_core.drift()))
                sync_core.write()
                self.assertEqual(sync_core.drift(), [])
                plugin, (pkg, _, _) = next(iter(sync_core.COMPANIONS.items()))
                core = os.path.join(d, "plugins", plugin, pkg, "_core")
                with open(os.path.join(core, "markers.py"), "a", encoding="utf-8") as f:
                    f.write("# hand edit\n")
                with open(os.path.join(core, "gone.py"), "w", encoding="utf-8") as f:
                    f.write("")
                kinds = sorted(p.split()[0] for p in sync_core.drift())
                self.assertEqual(kinds, ["differs", "stale"])
                sync_core.write()
                self.assertEqual(sync_core.drift(), [])
            finally:
                sync_core.ROOT = real_root

    def test_repo_is_in_sync(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import sync_core
        self.assertEqual(sync_core.drift(), [], "run: python3 tools/sync_core.py")


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


class TestRunContract(unittest.TestCase):
    def _run(self, d, state="OK_FOR_REVIEW", rel=False, final="report.md"):
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        _write(a, {"schema": "a@1", "produced_by": "ext", "data": {"x": 1},
                   "trace": [{"value": "1", "source": "in.txt", "locator": "line 1"}]})
        _write(b, {"schema": "b@1", "produced_by": "calc", "data": {"y": 2},
                   "trace": [{"value": "1", "source": "in.txt", "locator": "line 1"},
                             {"value": "2", "source": "in.txt", "locator": "line 2"}]})
        with open(os.path.join(d, "report.md"), "w", encoding="utf-8") as f:
            f.write("# r\n")
        ref = (lambda p: os.path.basename(p)) if rel else (lambda p: p)
        mani = {"flow": "f", "run_id": "r1", "steps": [
            {"skill": "ext", "ok": True, "out": ref(a)},
            {"skill": "branch→calc", "ok": True, "out": ref(a)},
            {"skill": "calc", "ok": True, "out": ref(b)},
            {"skill": "report", "ok": True, "out": ref(os.path.join(d, final))}],
            "final_output": ref(os.path.join(d, final))}
        if state is not None:
            mani["state"] = state
        _write(os.path.join(d, run_contract.MANIFEST), mani)

    def test_reads_contract(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d)
            rc = run_contract.load(d)
            self.assertEqual((rc.run_id, rc.flow, rc.state), ("r1", "f", "OK_FOR_REVIEW"))
            self.assertEqual([s.skill for s in rc.steps], ["ext", "calc", "report"])  # branch skipped
            self.assertEqual([os.path.basename(a.path) for a in rc.json_artifacts()], ["a.json", "b.json"])
            self.assertEqual(len(rc.pooled_trace()), 2)  # deduped across artifacts
            feed = rc.feeding_artifact()
            self.assertEqual((feed.produced_by, feed.data), ("calc", {"y": 2}))
            self.assertEqual(rc.produced_by, "calc")
            self.assertTrue(rc.final_output.endswith("report.md"))

    def test_relocated_run_resolves_by_basename(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, rel=True)
            rc = run_contract.load(d)
            self.assertEqual(len(rc.json_artifacts()), 2)
            self.assertTrue(os.path.isabs(rc.final_output))

    def test_json_final_output_feeds(self):
        with tempfile.TemporaryDirectory() as d:
            self._run(d, final="a.json")
            self.assertEqual(run_contract.load(d).feeding_artifact().produced_by, "ext")

    def test_refuses_failed_and_stateless_runs(self):
        for state in ("FAILED", None):
            with tempfile.TemporaryDirectory() as d:
                self._run(d, state=state)
                with self.assertRaises(run_contract.RunNotReviewable) as cm:
                    run_contract.load(d)
                self.assertIn("OK_FOR_REVIEW", str(cm.exception))

    def test_missing_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(run_contract.NotAKitRun):
                run_contract.load(d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
