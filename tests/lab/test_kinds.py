import json
import shutil
import unittest

from conformance.lab.engines.base import Outcome
from conformance.lab.engines.native import NativeEngine
from conformance.lab.errors import PlanError
from conformance.lab.kinds import adequacy, verification
from tests.lab.helpers import FIXTURES, LabTest


class ClassificationTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(adequacy.classify(Outcome("a", 2, 1)), "killed")
        self.assertEqual(adequacy.classify(Outcome("a", 0, 1)), "killed_crash")
        self.assertEqual(adequacy.classify(Outcome("a", 0, 0)), "survived")
        self.assertEqual(adequacy.classify(Outcome("a", 3, 0, "unproved")), "not_measured")

    def test_row_status(self):
        good = {"positive": Outcome("p", 1, 0), "inert": Outcome("i", 0, 0)}
        self.assertEqual(adequacy.row_status(good), "MEASURED")
        self.assertEqual(adequacy.row_status({**good, "positive": Outcome("p", 0, 0)}), "VOID_NO_SCORE")
        self.assertEqual(adequacy.row_status({**good, "positive": Outcome("p", 0, 2)}), "VOID_NO_SCORE")
        self.assertEqual(adequacy.row_status({**good, "inert": Outcome("i", 1, 0)}), "VOID")
        self.assertEqual(adequacy.row_status({**good, "inert": Outcome("i", 0, 1)}), "VOID")


class AdequacyRowTest(LabTest):
    def setUp(self):
        super().setUp()
        self.run = self.copy_fixture("toy-run", self.tmp / "run")
        self.tree = self.tmp / "tree"
        shutil.copytree(FIXTURES / "toy-subject", self.tree)
        adequacy.prepare_tree(self.run, self.tree)
        self.scope = json.loads((self.run / "SCOPE.json").read_text(encoding="utf-8"))
        self.row = self.scope["rows"][0]

    def test_toy_row(self):
        result, report = adequacy.execute_row(self.run, self.scope, self.tree, self.row, NativeEngine())
        self.assertIsNone(report)
        self.assertEqual(result["status"], "MEASURED")
        outcomes = {m["fault_id"]: m["outcome"] for m in result["mutants"]}
        self.assertEqual(outcomes, {"F1": "killed", "F2": "killed", "F3": "survived", "F4": "killed_crash"})
        self.assertEqual(result["counts_by_set"],
                         {"toy-known": {"killed": 2, "killed_crash": 1, "survived": 1, "not_measured": 0}})
        survivor = next(m for m in result["mutants"] if m["fault_id"] == "F3")
        self.assertIn("not a checker defect", survivor["note"])

    def test_sets_are_counted_separately(self):
        held = json.loads((self.run / "faults" / "known.json").read_text(encoding="utf-8"))
        held.update(name="toy-held-out", set="held_out", faults=[{**held["faults"][2], "id": "H1"}])
        (self.run / "faults" / "held.json").write_text(json.dumps(held), encoding="utf-8")
        self.row["fault_sets"].append("faults/held.json")
        result, _ = adequacy.execute_row(self.run, self.scope, self.tree, self.row, NativeEngine())
        self.assertEqual(set(result["counts_by_set"]), {"toy-known", "toy-held-out"})
        self.assertEqual(result["counts_by_set"]["toy-held-out"]["survived"], 1)

    def test_positive_control_that_survives_voids_the_row(self):
        control = json.loads((self.run / "controls" / "positive.json").read_text(encoding="utf-8"))
        control.update(anchor="if case.get(\"expired\"):", replacement="if False:")
        (self.run / "controls" / "positive.json").write_text(json.dumps(control), encoding="utf-8")
        result, _ = adequacy.execute_row(self.run, self.scope, self.tree, self.row, NativeEngine())
        self.assertEqual(result["status"], "VOID_NO_SCORE")

    def test_baseline_must_match_subject_expectations(self):
        cases = json.loads((self.tree / "cases.json").read_text(encoding="utf-8"))
        cases["cases"][0]["expected"]["reason"] = "different"
        (self.tree / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "T1"):
            adequacy.execute_row(self.run, self.scope, self.tree, self.row, NativeEngine())


class VerificationTest(LabTest):
    def setUp(self):
        super().setUp()
        self.run = self.copy_fixture("toy-verification-run", self.tmp / "run")
        self.scope = json.loads((self.run / "SCOPE.json").read_text(encoding="utf-8"))
        self.trees = {0: FIXTURES / "toy-receipts"}

    def records(self):
        return {(r["input"], r["claim"]): r for r in verification.execute(self.run, self.scope, self.trees)}

    def test_per_claim_results(self):
        records = self.records()
        self.assertEqual(records[("within", "cap_compliance")]["result"], "ESTABLISHED")
        self.assertEqual(records[("over", "cap_compliance")]["result"], "CONTRADICTED")
        self.assertEqual(records[("over", "exact_call")]["result"], "CONTRADICTED")
        self.assertEqual(records[("within", "signature")]["result"], "NOT_ESTABLISHED")
        self.assertEqual(records[("within", "signature")]["unresolved_obligations"], ["signature_key_pin"])
        self.assertTrue(records[("over", "cap_compliance")]["evidence"][0].startswith("sha256:"))

    def write_verifier(self, body):
        (self.run / "verifier" / "receipts.py").write_text(body, encoding="utf-8")

    def test_exception_is_an_error_not_a_result(self):
        self.write_verifier("def cap_compliance(d, c):\n    raise KeyError('x')\n"
                            "exact_call = signature = cap_compliance\n")
        record = self.records()[("within", "cap_compliance")]
        self.assertEqual((record["execution"], record["result"]), ("ERROR", None))
        self.assertEqual(record["verifier_error"]["code"], "exception")

    def test_undeclared_read_is_an_error(self):
        self.write_verifier("def cap_compliance(d, c):\n    return {'result': 'ESTABLISHED', 'reads': ['execution.amount']}\n"
                            "exact_call = signature = cap_compliance\n")
        self.assertEqual(self.records()[("within", "cap_compliance")]["verifier_error"]["code"], "undeclared_read")

    def test_not_established_needs_obligations(self):
        self.write_verifier("def cap_compliance(d, c):\n    return {'result': 'NOT_ESTABLISHED', 'reads': []}\n"
                            "exact_call = signature = cap_compliance\n")
        self.assertEqual(self.records()[("within", "cap_compliance")]["verifier_error"]["code"], "missing_obligations")

    def test_checks_never_see_expectations(self):
        self.write_verifier("def cap_compliance(d, c):\n    assert set(c) == {'reference_time'}\n"
                            "    assert 'expected' not in d\n    return {'result': 'ESTABLISHED', 'reads': []}\n"
                            "exact_call = signature = cap_compliance\n")
        self.assertEqual(self.records()[("within", "cap_compliance")]["execution"], "COMPLETED")

    def test_agreement_is_reported_separately(self):
        records = verification.execute(self.run, self.scope, self.trees)
        report = verification.agreement(self.run, records)
        rows = {(r["input"], r["claim"]): r["agree"] for r in report["rows"]}
        self.assertTrue(rows[("over", "cap_compliance")])
        self.assertFalse(rows[("over", "exact_call")])  # producer fixture deliberately disagrees
        self.assertIn("not a result", report["note"])


if __name__ == "__main__":
    unittest.main()
