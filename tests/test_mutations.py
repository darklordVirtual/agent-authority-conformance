import json
import unittest

from conformance import mutations
from conformance.validation import ROOT


class MutationHarnessTests(unittest.TestCase):
    def setUp(self):
        self.definitions = mutations.load_definitions()
        self.fixtures = mutations.load_fixtures()
        self.source = mutations.SUBJECT.read_text(encoding="utf-8")

    def test_every_anchor_occurs_exactly_once(self):
        for mutation in self.definitions["mutations"]:
            with self.subTest(mutation=mutation["id"]):
                self.assertEqual(self.source.count(mutation["anchor"]), 1)
                self.assertNotEqual(mutation["anchor"], mutation["replacement"])

    def test_controls_behave_and_no_mutation_survives(self):
        report = mutations.sweep(self.definitions, self.fixtures, self.source)
        rows = {row["id"]: row for row in report["rows"]}
        self.assertEqual(rows["CONTROL-positive"]["status"], "killed")
        self.assertEqual(rows["CONTROL-inert"]["status"], "survived")
        self.assertEqual(report["survived"], [], "a surviving mutation is a gap in the fixture corpus")
        self.assertEqual(report["killed"], report["mutations"] - len(report["declared_equivalent"]))

    def test_declared_equivalents_carry_a_reason(self):
        for mutation in self.definitions["mutations"]:
            if "equivalent" in mutation:
                self.assertTrue(mutation["equivalent"].strip(), mutation["id"])

    def test_mutated_source_never_reaches_disk(self):
        before = mutations.SUBJECT.read_bytes()
        mutations.sweep(self.definitions, self.fixtures, self.source)
        self.assertEqual(mutations.SUBJECT.read_bytes(), before)
        for path in sorted((ROOT / "tests" / "fixtures").glob("*.json")):
            json.loads(path.read_text(encoding="utf-8"))

    def test_a_broken_positive_control_is_a_harness_error_not_a_result(self):
        definitions = json.loads(json.dumps(self.definitions))
        for mutation in definitions["mutations"]:
            if mutation.get("control") == "positive":
                mutation["anchor"] = "\"\"\"Return a scoped property verdict; errors are distinct non-verdicts.\"\"\""
                mutation["replacement"] = "\"\"\"Return a scoped property verdict (no-op).\"\"\""
        with self.assertRaises(mutations.HarnessError):
            mutations.sweep(definitions, self.fixtures, self.source)

    def test_a_disagreeing_original_is_a_harness_error(self):
        broken = self.source.replace("    return result(\"PASS\", [])\n", "    return result(\"FAIL\", [])\n")
        with self.assertRaises(mutations.HarnessError):
            mutations.sweep(self.definitions, self.fixtures, broken)

    def test_an_unexpected_exception_counts_as_a_kill_not_a_verdict(self):
        crashing = self.source.replace("    context = document[\"context\"]\n",
                                       "    raise RuntimeError(\"boom\")\n    context = document[\"context\"]\n")
        rule = mutations.load_rule(crashing, "crash")
        outcome = mutations.outcome_of(rule, self.fixtures[0]["input"])
        self.assertEqual(outcome["verification_status"], "ERROR")
        self.assertIsNone(outcome["status"])
        self.assertTrue(mutations.score(rule, self.fixtures))

    def test_definitions_digest_is_stable_and_normalised(self):
        digest = mutations.definitions_digest()
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, mutations.definitions_digest())


if __name__ == "__main__":
    unittest.main()
