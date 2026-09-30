import itertools
import json
import unittest

from conformance import invariants
from conformance.boundary import evaluate
from conformance.validation import ROOT


def fixture_inputs():
    """Fixture inputs the rule accepts; invalid-input and unsupported fixtures are non-verdicts."""
    for path in sorted((ROOT / "tests" / "fixtures").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture["expected"].get("status") in ("PASS", "FAIL", "NOT_ESTABLISHED"):
            yield fixture["id"], fixture["input"]


class InvariantTests(unittest.TestCase):
    def test_relations_hold_on_every_committed_fixture_input(self):
        for fixture_id, doc in fixture_inputs():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(invariants.relation_failures(doc), [])

    def test_relations_hold_on_a_sample_of_the_generated_space(self):
        sample = list(itertools.islice(invariants.generated_space(max_attempts=3), 0, None, 7))
        self.assertGreater(len(sample), 100)
        checked, failures = invariants.check(sample)
        self.assertEqual(checked, len(sample))
        self.assertEqual(failures, [])

    def test_reference_model_agrees_with_the_rule_on_the_full_space_which_reaches_every_verdict(self):
        """One pass over the whole space: differential agreement, and no verdict or obligation is unreachable."""
        statuses = set()
        obligations = set()
        disagreements = []
        for doc in invariants.generated_space(max_attempts=5):
            result = evaluate(json.loads(json.dumps(doc)))
            if result != invariants.reference_model(doc):
                disagreements.append(doc)
            statuses.add(result["status"])
            obligations.update(result["unresolved_obligations"])
        self.assertEqual(disagreements, [])
        self.assertEqual(statuses, {"PASS", "FAIL", "NOT_ESTABLISHED"})
        self.assertEqual(obligations, set(invariants.OBLIGATION_ORDER))

    def test_a_relation_failure_is_reported_not_swallowed(self):
        """A rule that ignores scope must break INV-4; the relation set is not decoration."""
        doc = next(doc for _, doc in fixture_inputs() if evaluate(json.loads(json.dumps(doc)))["status"] == "PASS")
        original = invariants.evaluate

        def scope_blind(document):
            document = json.loads(json.dumps(document))
            for a in document["attempts"]:
                a["scope"] = document["context"]["evaluation_scope"]
            return original(document)

        invariants.evaluate = scope_blind
        try:
            failures = invariants.relation_failures(doc)
        finally:
            invariants.evaluate = original
        self.assertIn("INV-4 out-of-scope attempt", failures)

    def test_cli_reports_and_exits_zero(self):
        self.assertEqual(invariants.main(["--max-attempts", "2"]), 0)


if __name__ == "__main__":
    unittest.main()
