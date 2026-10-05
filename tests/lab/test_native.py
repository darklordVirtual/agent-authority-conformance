import json
import shutil
import unittest

from conformance.lab.engines.base import get_engine
from conformance.lab.engines.native import CRASH, NativeEngine
from conformance.lab.errors import EngineError
from conformance.lab.faults import row_mutations
from tests.lab.helpers import FIXTURES, LabTest


class NativeEngineTest(LabTest):
    def setUp(self):
        super().setUp()
        self.tree = self.tmp / "tree"
        shutil.copytree(FIXTURES / "toy-subject", self.tree)
        shutil.copy(FIXTURES / "toy-run" / "adapter" / "case.py", self.tree / "case.py")
        self.scope = json.loads((FIXTURES / "toy-run" / "SCOPE.json").read_text(encoding="utf-8"))
        self.row = self.scope["rows"][0]
        self.engine = NativeEngine(timeout=30)

    def test_toy_outcomes(self):
        controls, faults = row_mutations(FIXTURES / "toy-run", self.scope, self.row)
        result = self.engine.measure(self.tree, self.row, controls, faults)
        by_id = {o.fault_id: o for o in result["faults"]}
        self.assertEqual((by_id["F1"].moved, by_id["F1"].crashed), (1, 0))
        self.assertEqual((by_id["F2"].moved, by_id["F2"].crashed), (1, 0))
        self.assertEqual((by_id["F3"].moved, by_id["F3"].crashed), (0, 0))
        self.assertEqual((by_id["F4"].moved, by_id["F4"].crashed), (0, 1))
        self.assertEqual(by_id["F4"].diff["T1"]["mutant"], CRASH)
        self.assertEqual(result["controls"]["positive"].moved, 1)
        self.assertEqual((result["controls"]["inert"].moved, result["controls"]["inert"].crashed), (0, 0))

    def test_baseline_crash_is_an_engine_error(self):
        (self.tree / "checker.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
        with self.assertRaisesRegex(EngineError, "baseline crashed"):
            self.engine.baseline(self.tree, self.row)

    def test_missing_projection_field_is_a_crash(self):
        row = {**self.row, "projection": ["status", "missing"]}
        self.assertEqual(self.engine.run_case(self.tree, row, 0, "T1"), CRASH)

    def test_warning_lines_before_projection(self):
        adapter = (self.tree / "case.py").read_text(encoding="utf-8")
        (self.tree / "case.py").write_text(
            adapter.replace("print(json.dumps(", "print('warning: noisy adapter')\nprint(json.dumps("),
            encoding="utf-8")
        self.assertEqual(self.engine.run_case(self.tree, self.row, 0, "T1"),
                         {"status": "accepted", "reason": "ok"})

    def test_case_id_with_slash(self):
        cases = json.loads((self.tree / "cases.json").read_text(encoding="utf-8"))
        cases["cases"][0]["id"] = "group/T 1"
        (self.tree / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
        row = {**self.row, "cases": ["group/T 1"]}
        self.assertEqual(self.engine.baseline(self.tree, row), {"group/T 1": {"status": "accepted", "reason": "ok"}})

    def test_crlf_anchor(self):
        source = (self.tree / "checker.py").read_bytes().replace(b"\n", b"\r\n")
        (self.tree / "checker.py").write_bytes(source)
        mutation = {"id": "CR", "file": "checker.py", "anchor": "if case.get(\"expired\"):\r\n",
                    "replacement": "if case.get(\"expired\") or True:\r\n"}
        base = self.engine.baseline(self.tree, self.row)
        outcome = self.engine.mutant(self.tree, self.row, mutation, base)
        self.assertEqual(outcome.moved, 1)  # T1 now reads as expired
        self.assertEqual((self.tree / "checker.py").read_bytes(), source)  # original tree untouched

    def test_timeout_is_a_crash(self):
        (self.tree / "case.py").write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
        self.assertEqual(NativeEngine(timeout=1).run_case(self.tree, self.row, 0, "T1"), CRASH)

    def test_get_engine(self):
        self.assertEqual(get_engine({"name": "native"}).name, "native")
        with self.assertRaises(ValueError):
            get_engine({"name": "other"})


if __name__ == "__main__":
    unittest.main()
