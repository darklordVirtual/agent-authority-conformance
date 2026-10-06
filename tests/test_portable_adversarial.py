from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from aacp.cli import main as cli_main
from aacp.adversarial import CASES, PROPERTIES, classify, run


ROOT = Path(__file__).parents[1]


class PortableAdversarialTests(unittest.TestCase):
    def test_vectors_are_vendor_neutral_and_do_not_embed_expectations(self):
        encoded = json.dumps(CASES, sort_keys=True).lower()
        self.assertNotIn("remora", encoded)
        self.assertNotIn("executionlease", encoded)
        self.assertNotIn("governedtooldispatcher", encoded)
        for case in CASES:
            self.assertIn(case["property"], PROPERTIES)
            self.assertNotIn("expected", case)
            self.assertNotIn("verdict", case)
            self.assertNotIn("result", case)
            self.assertTrue(case["claim_ceiling"])

    def test_case_ids_are_unique_and_cover_c_f_g(self):
        ids = [case["id"] for case in CASES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({case["property"] for case in CASES}, set(PROPERTIES))

    def test_exact_call_late_mutation_is_contradicted(self):
        case = next(case for case in CASES if case["id"] == "C-04")
        result = classify(case, {
            "execution": "COMPLETED",
            "outcome": "EXECUTED",
            "executed_call": case["challenge"]["late_mutation"],
        })
        self.assertEqual(result["result"], "CONTRADICTED")

    def test_exact_call_refusal_is_established(self):
        case = next(case for case in CASES if case["id"] == "C-01")
        result = classify(case, {"execution": "COMPLETED", "outcome": "REFUSED"})
        self.assertEqual(result["result"], "ESTABLISHED")

    def test_freshness_execution_after_context_change_is_contradicted(self):
        case = next(case for case in CASES if case["id"] == "F-02")
        result = classify(case, {"execution": "COMPLETED", "outcome": "EXECUTED"})
        self.assertEqual(result["result"], "CONTRADICTED")

    def test_missing_vs_null_false_verified_is_contradicted(self):
        case = next(case for case in CASES if case["id"] == "G-01")
        result = classify(case, {
            "execution": "COMPLETED",
            "effect_status": "EFFECT_VERIFIED",
        })
        self.assertEqual(result["result"], "CONTRADICTED")

    def test_invalid_rule_cannot_verify(self):
        case = next(case for case in CASES if case["id"] == "G-02")
        result = classify(case, {
            "execution": "COMPLETED",
            "effect_status": "EFFECT_VERIFIED",
        })
        self.assertEqual(result["result"], "CONTRADICTED")
        refused = classify(case, {
            "execution": "COMPLETED",
            "outcome": "INVALID_INPUT",
        })
        self.assertEqual(refused["result"], "ESTABLISHED")

    def test_forged_receipt_acceptance_is_contradicted(self):
        case = next(case for case in CASES if case["id"] == "G-05")
        result = classify(case, {"execution": "COMPLETED", "outcome": "ACCEPTED"})
        self.assertEqual(result["result"], "CONTRADICTED")

    def test_terminal_slot_poisoning_is_contradicted(self):
        case = next(case for case in CASES if case["id"] == "G-07")
        result = classify(case, {
            "execution": "COMPLETED",
            "steps": [
                {"id": "unbound_unsupported", "outcome": "ACCEPTED"},
                {"id": "legitimate_verified", "outcome": "REFUSED"},
            ],
        })
        self.assertEqual(result["result"], "CONTRADICTED")

    def test_unsupported_is_a_non_verdict(self):
        case = next(case for case in CASES if case["id"] == "F-03")
        result = classify(case, {"execution": "UNSUPPORTED", "message": "no hook"})
        self.assertEqual(result["execution"], "UNSUPPORTED")
        self.assertIsNone(result["result"])

    def test_runner_never_passes_expected_answer_to_adapter(self):
        seen = []

        def adapter(case):
            seen.append(case)
            return {"execution": "UNSUPPORTED", "message": "fixture adapter"}

        document = run(adapter, ("C",))
        self.assertTrue(seen)
        for case in seen:
            self.assertNotIn("expected", case)
            self.assertNotIn("result", case)
            self.assertNotIn("verdict", case)
        self.assertEqual(document["independence"], "SELF_RUN")
        self.assertEqual(document["bcr_level"], "BCR-0")

    def test_cli_exposes_machine_readable_vectors(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli_main(["adversarial", "--list", "--json"])
        self.assertEqual(code, 0)
        document = json.loads(output.getvalue())
        self.assertEqual(document["suite_version"], "aacp-portable-cfg-adversarial-v1")
        self.assertEqual({row["property"] for row in document["cases"]}, {"C", "F", "G"})
        self.assertTrue(all("challenge" in row for row in document["cases"]))

    def test_run_record_matches_schema(self):
        def adapter(case):
            return {"execution": "UNSUPPORTED", "message": "fixture adapter"}

        document = run(adapter)
        schema = json.loads(
            (ROOT / "schema" / "aacp-adversarial-run-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(document)


if __name__ == "__main__":
    unittest.main()
