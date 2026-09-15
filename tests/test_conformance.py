import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import ValidationError

from conformance.boundary import InvalidInput, UnsupportedVerification, evaluate
from conformance.check import check_fixture
from conformance.validation import ROOT, load_validator, validate_assessment


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def reference():
    return {"kind": "fixture", "reference": "fixture:synthetic",
            "revision": "synthetic-model-v1", "description": "Schema test only"}


def completed(status="PASS", property_id="C"):
    doc = read("examples/v0.2/minimal.json")
    row = doc["properties"][0]
    row.update(status=status, verification_status="COMPLETED",
               evaluation_scope="synthetic-zone-v1/session-1",
               procedure=reference(), unresolved_obligations=[])
    if status in {"PASS", "FAIL"}:
        row.update(evidence_tier="RESOLVED", evidence=[reference()])
    if status == "PASS":
        row["supported_scope"] = "synthetic scope only"
    if status == "NOT_ESTABLISHED":
        row["unresolved_obligations"] = ["argument_binding_evidence"]
    if property_id == "E":
        row.update(id="E", property="Execution-Boundary Integrity")
        row["execution_boundary"] = {
            "evaluation_scope": row["evaluation_scope"], "agent_zone": "synthetic roots",
            "attempted_bypass_classes": [a["class"] for a in
                read("tests/fixtures/bounded-pass.json")["input"]["attempts"]],
            "topology_evidence": reference(), "coverage_evidence": reference(),
            "bypass_evidence": [reference()]}
    return doc


class SchemaTests(unittest.TestCase):
    def test_all_schemas_and_examples(self):
        for path in (ROOT / "schema").glob("*.json"):
            load_validator(path.name)
        for path in (ROOT / "examples").rglob("*.json"):
            with self.subTest(path=path):
                validate_assessment(json.loads(path.read_text(encoding="utf-8")))

    def test_all_valid_result_states(self):
        for status in ("PASS", "FAIL", "NOT_ESTABLISHED"):
            with self.subTest(status=status):
                validate_assessment(completed(status))
        for status in ("UNTESTED", "OUT_OF_SCOPE"):
            doc = read("examples/v0.2/minimal.json")
            doc["properties"][0]["status"] = status
            validate_assessment(doc)
        for state in ("INVALID_INPUT", "UNSUPPORTED", "ERROR"):
            doc = read("examples/v0.2/minimal.json")
            doc["properties"][0].update(status=None, verification_status=state,
                verifier_error={"code": "example", "message": "No verdict"})
            validate_assessment(doc)
        validate_assessment(completed(property_id="E"))

    def test_pass_fail_require_resolved_nonempty_pinned_evidence(self):
        for status in ("PASS", "FAIL"):
            for mutation in ("empty", "reported", "none", "missing_revision", "blank_revision"):
                with self.subTest(status=status, mutation=mutation):
                    doc = completed(status)
                    row = doc["properties"][0]
                    if mutation == "empty":
                        row["evidence"] = []
                    elif mutation in {"reported", "none"}:
                        row["evidence_tier"] = mutation.upper()
                    elif mutation == "missing_revision":
                        del row["evidence"][0]["revision"]
                    else:
                        row["evidence"][0]["revision"] = "  "
                    with self.assertRaises(ValidationError):
                        validate_assessment(doc)

    def test_unique_ids_and_matching_names(self):
        doc = completed()
        doc["properties"].append(copy.deepcopy(doc["properties"][0]))
        with self.assertRaises(ValidationError):
            validate_assessment(doc)
        doc["properties"].pop()
        doc["properties"][0]["property"] = "Effect Verification"
        with self.assertRaises(ValidationError):
            validate_assessment(doc)

    def test_not_established_requires_completed_procedure_and_obligation(self):
        for field in ("procedure", "evaluation_scope", "unresolved_obligations"):
            doc = completed("NOT_ESTABLISHED")
            del doc["properties"][0][field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_assessment(doc)
        doc = completed("NOT_ESTABLISHED")
        doc["properties"][0]["unresolved_obligations"] = []
        with self.assertRaises(ValidationError):
            validate_assessment(doc)

    def test_verifier_states_cannot_be_property_verdicts(self):
        for state in ("NOT_RUN", "INVALID_INPUT", "UNSUPPORTED", "ERROR"):
            for status in ("PASS", "FAIL", "NOT_ESTABLISHED"):
                doc = completed(status)
                row = doc["properties"][0]
                row["verification_status"] = state
                if state != "NOT_RUN":
                    row["verifier_error"] = {"code": "example", "message": "failed"}
                with self.subTest(state=state, status=status), self.assertRaises(ValidationError):
                    validate_assessment(doc)

    def test_completed_cannot_carry_verifier_error(self):
        doc = completed()
        doc["properties"][0]["verifier_error"] = {"code": "error", "message": "failed"}
        with self.assertRaises(ValidationError):
            validate_assessment(doc)

    def test_e_pass_requires_both_evidence_halves_and_scope_match(self):
        for field in ("topology_evidence", "coverage_evidence", "bypass_evidence",
                      "agent_zone", "attempted_bypass_classes"):
            doc = completed(property_id="E")
            del doc["properties"][0]["execution_boundary"][field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_assessment(doc)
        for mutation in ("wrong_scope", "missing_class", "no_boundary"):
            doc = completed(property_id="E")
            row = doc["properties"][0]
            if mutation == "wrong_scope":
                row["execution_boundary"]["evaluation_scope"] = "other"
            elif mutation == "missing_class":
                row["execution_boundary"]["attempted_bypass_classes"].pop()
            else:
                del row["execution_boundary"]
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                validate_assessment(doc)

    def test_no_scores_and_real_dates(self):
        for key, value in (("score", 100), ("assessed_at", "2026-02-30"),
                           ("spec_version", "0.3"), ("system", "   ")):
            doc = completed()
            doc[key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validate_assessment(doc)

    def test_readme_example_is_valid_and_matches_file(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        snippet = text.split("```json\n", 1)[1].split("```", 1)[0]
        doc = json.loads(snippet)
        validate_assessment(doc)
        self.assertEqual(doc, read("examples/v0.2/minimal.json"))

    def test_v01_files_are_byte_preserved(self):
        expected = {
            "SPECIFICATION.md": "bacb4ac1c050fff66f0132d84bac933f58a150ce",
            "schema/assessment.schema.json": "2fa713f00e2ecb34284c64342f4f41ef138d58ad",
            "examples/aegis-core-3.4.0.json": "29bcfd011f687767c9c2d2b9900d39dfdd9d2cb5",
        }
        for path, digest in expected.items():
            data = (ROOT / path).read_bytes()
            actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            self.assertEqual(actual, digest, path)

    def test_example_references_match_committed_content(self):
        doc = read("examples/v0.2/not-established.json")
        row = doc["properties"][0]
        for ref in [row["procedure"], *row["evidence"]]:
            actual = "sha256:" + hashlib.sha256((ROOT / ref["reference"]).read_bytes()).hexdigest()
            self.assertEqual(ref["revision"], actual, ref["reference"])
        self.assertEqual(doc["revision"], row["evidence"][0]["revision"])
        fixture = read(row["evidence"][0]["reference"])
        result = evaluate(fixture["input"])
        self.assertEqual(row["status"], result["status"])
        self.assertEqual(row["unresolved_obligations"], result["unresolved_obligations"])


class BoundaryTests(unittest.TestCase):
    def test_committed_fixtures(self):
        for path in sorted((ROOT / "tests/fixtures").glob("*.json")):
            with self.subTest(path=path.name):
                check_fixture(path)

    def test_removing_evidence_never_preserves_pass(self):
        baseline = read("tests/fixtures/bounded-pass.json")["input"]
        for key in ("accepted_coverage", "accepted_topology"):
            doc = copy.deepcopy(baseline)
            doc["context"][key] = None
            self.assertEqual(evaluate(doc)["status"], "NOT_ESTABLISHED")
        for i in range(len(baseline["attempts"])):
            doc = copy.deepcopy(baseline)
            doc["attempts"].pop(i)
            self.assertEqual(evaluate(doc)["status"], "NOT_ESTABLISHED")

    def test_missing_descriptors_and_wrong_types_are_invalid(self):
        for field in ("scope", "outcome", "reference", "revision", "class"):
            doc = read("tests/fixtures/bounded-pass.json")["input"]
            del doc["attempts"][0][field]
            with self.subTest(field=field), self.assertRaises(InvalidInput):
                evaluate(doc)
        for value in (False, 0, "", [], {}):
            doc = read("tests/fixtures/bounded-pass.json")["input"]
            doc["context"]["accepted_coverage"] = value
            with self.subTest(value=value), self.assertRaises(InvalidInput):
                evaluate(doc)

    def test_unknown_property_is_not_a_verdict(self):
        doc = read("tests/fixtures/unsupported-property.json")["input"]
        with self.assertRaises(UnsupportedVerification):
            evaluate(doc)

    def test_expectations_do_not_influence_checker(self):
        fixture = read("tests/fixtures/missing-coverage.json")
        before = copy.deepcopy(fixture["input"])
        first = evaluate(fixture["input"])
        fixture["expected"]["status"] = "PASS"
        self.assertEqual(evaluate(fixture["input"]), first)
        self.assertEqual(fixture["input"], before)
        doc = copy.deepcopy(before)
        doc["unmet_proof_obligation"] = "observation_coverage"
        with self.assertRaises(InvalidInput):
            evaluate(doc)

    def test_tampered_expectation_fails_without_repair(self):
        fixture = read("tests/fixtures/missing-coverage.json")
        fixture["expected"]["status"] = "PASS"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tampered.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run([sys.executable, "-m", "conformance.check",
                                     "--fixtures", folder], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected", result.stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_default_runner_is_read_only(self):
        paths = list((ROOT / "tests/fixtures").glob("*.json"))
        before = {p: p.read_bytes() for p in paths}
        result = subprocess.run([sys.executable, "-m", "conformance.check"], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({p: p.read_bytes() for p in paths}, before)


if __name__ == "__main__":
    unittest.main()
