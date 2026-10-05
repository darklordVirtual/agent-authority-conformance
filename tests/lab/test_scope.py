import copy
import json
import unittest

from conformance.lab import faults
from conformance.lab.errors import PlanError, ScopeError
from conformance.lab.scope import validate_scope
from tests.lab.helpers import FIXTURES, LabTest


def fixture_scope(name):
    return json.loads((FIXTURES / name / "SCOPE.json").read_text(encoding="utf-8"))


class ScopeTest(unittest.TestCase):
    def setUp(self):
        self.adequacy = fixture_scope("toy-run")
        self.verification = fixture_scope("toy-verification-run")

    def invalid(self, scope, needle):
        with self.assertRaisesRegex(ScopeError, needle):
            validate_scope(scope)

    def test_fixtures_are_valid(self):
        validate_scope(self.adequacy)
        validate_scope(self.verification)

    def test_required_top_level_fields(self):
        for key in ("lab_version", "run_id", "kind", "independence", "runner", "agreement_parties",
                    "subjects", "claim_ceiling", "publication"):
            with self.subTest(key=key):
                scope = copy.deepcopy(self.adequacy)
                del scope[key]
                with self.assertRaises(ScopeError):
                    validate_scope(scope)

    def test_aggregate_keys_are_rejected_anywhere(self):
        scope = copy.deepcopy(self.adequacy)
        scope["rows"][0]["score"] = 1
        self.invalid(scope, "aggregate key")

    def test_claim_ceiling_needs_both_sides(self):
        scope = copy.deepcopy(self.adequacy)
        scope["claim_ceiling"]["does_not_establish"] = []
        self.invalid(scope, "does_not_establish")

    def test_publication_must_be_private_first_and_not_citable(self):
        scope = copy.deepcopy(self.adequacy)
        scope["publication"]["private_first"] = False
        self.invalid(scope, "private_first")
        scope = copy.deepcopy(self.adequacy)
        scope["publication"]["unreleased_citable"] = True
        self.invalid(scope, "unreleased_citable")

    def test_independent_needs_statement(self):
        scope = copy.deepcopy(self.verification)
        del scope["independence_statement"]
        self.invalid(scope, "independence_statement")

    def test_short_commit_is_rejected(self):
        scope = copy.deepcopy(self.adequacy)
        scope["subjects"][0]["commit"] = "4404df2c"
        self.invalid(scope, "40-character")

    def test_pins_required_when_asked(self):
        with self.assertRaisesRegex(ScopeError, "run pin first"):
            validate_scope(copy.deepcopy(self.adequacy), require_pins=True)

    def test_absolute_or_parent_paths_rejected(self):
        for bad in ("/etc/passwd", "../x", "a/../../b"):
            scope = copy.deepcopy(self.adequacy)
            scope["subjects"][0]["paths"] = [bad]
            with self.subTest(path=bad):
                self.invalid(scope, "relative")

    def test_adequacy_measures_one_subject(self):
        scope = copy.deepcopy(self.adequacy)
        scope["subjects"].append(copy.deepcopy(scope["subjects"][0]))
        self.invalid(scope, "exactly one subject")

    def test_row_command_needs_case_placeholder(self):
        scope = copy.deepcopy(self.adequacy)
        scope["rows"][0]["command"] = ["python3", "case.py"]
        self.invalid(scope, "{case}")

    def test_cross_check_must_be_other_engine(self):
        scope = copy.deepcopy(self.adequacy)
        scope["engine"]["cross_check"] = "native"
        self.invalid(scope, "cross_check")

    def test_verification_cross_references(self):
        scope = copy.deepcopy(self.verification)
        scope["claims"][0]["inputs"] = ["missing"]
        self.invalid(scope, "declared inputs")
        scope = copy.deepcopy(self.verification)
        scope["inputs"][0]["subject"] = 3
        self.invalid(scope, "subject index")
        scope = copy.deepcopy(self.verification)
        scope["claims"][0]["check"] = "receipts.cap"
        self.invalid(scope, "check")

    def test_temporal_claim_needs_reference_time(self):
        scope = copy.deepcopy(self.verification)
        scope["claims"][0]["temporal"] = True
        self.invalid(scope, "reference_time")
        scope["reference_time"] = "2026-09-19T10:05:00Z"
        validate_scope(scope)


class FaultTest(LabTest):
    def test_fixture_faults_and_controls_load(self):
        run = FIXTURES / "toy-run"
        scope = fixture_scope("toy-run")
        controls, loaded = faults.row_mutations(run, scope, scope["rows"][0])
        self.assertEqual([f["id"] for f in loaded], ["F1", "F2", "F3", "F4"])
        self.assertEqual({f["set_name"] for f in loaded}, {"toy-known"})
        self.assertEqual(controls["positive"]["polarity"], "positive")

    def test_fault_set_needs_source_and_unique_ids(self):
        path = self.tmp / "f.json"
        path.write_text(json.dumps({"name": "n", "set": "known", "source": {"author": "a", "ref": "http://x"},
                                    "faults": [{"id": "A", "class": "c", "file": "f", "anchor": "x", "replacement": "y"},
                                               {"id": "A", "class": "c", "file": "f", "anchor": "x", "replacement": "z"}]}))
        with self.assertRaisesRegex(ScopeError, "https ref"):
            faults.load_fault_set(path)
        with self.assertRaisesRegex(ScopeError, "unique"):
            faults.load_fault_set(path)

    def test_control_polarity_must_match(self):
        with self.assertRaisesRegex(ScopeError, "polarity"):
            faults.load_control(FIXTURES / "toy-run" / "controls" / "inert.json", "positive")

    def test_apply_mutation_requires_a_unique_anchor(self):
        mutation = {"id": "X", "file": "f.py", "anchor": "a", "replacement": "b"}
        self.assertEqual(faults.apply_mutation("xay", mutation), "xby")
        with self.assertRaisesRegex(PlanError, "2 times"):
            faults.apply_mutation("aa", mutation)
        with self.assertRaisesRegex(PlanError, "0 times"):
            faults.apply_mutation("zz", mutation)

    def test_crlf_is_preserved(self):
        path = self.tmp / "crlf.py"
        path.write_bytes(b"if a:\r\n    pass\r\n")
        text = faults.read_source(path)
        mutation = {"id": "X", "file": "crlf.py", "anchor": "if a:\r\n", "replacement": "if b:\r\n"}
        faults.write_source(path, faults.apply_mutation(text, mutation))
        self.assertEqual(path.read_bytes(), b"if b:\r\n    pass\r\n")


if __name__ == "__main__":
    unittest.main()
