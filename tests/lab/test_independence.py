import copy
import json
import unittest

from conformance.lab import independence
from conformance.lab.errors import ScopeError
from conformance.lab.scope import validate_scope
from tests.lab.helpers import FIXTURES


def scope(name="toy-verification-run"):
    return json.loads((FIXTURES / name / "SCOPE.json").read_text(encoding="utf-8"))


class IndependenceTest(unittest.TestCase):
    def test_reproduction_is_a_valid_label(self):
        s = scope()
        s["independence"] = "REPRODUCTION"
        validate_scope(s)

    def test_claim_override_needs_reason(self):
        s = scope()
        s["claims"][0]["independent"] = False
        with self.assertRaises(ScopeError):
            validate_scope(s)
        s["claims"][0]["not_independent_reason"] = "runner authored the cap fixture"
        validate_scope(s)
        per = independence.per_claim(s)
        self.assertEqual(per["cap_compliance"], {"independent": False, "reason": "runner authored the cap fixture"})
        self.assertTrue(per["exact_call"]["independent"])

    def test_claim_cannot_claim_more_than_the_run(self):
        s = scope()
        s["independence"] = "SECOND_IMPLEMENTATION"
        s.pop("independence_statement")
        s["claims"][0]["independent"] = True
        with self.assertRaises(ScopeError):
            validate_scope(s)

    def test_non_independent_label_applies_to_every_claim(self):
        s = scope()
        s["independence"] = "SECOND_IMPLEMENTATION"
        s.pop("independence_statement")
        per = independence.per_claim(s)
        self.assertFalse(any(v["independent"] for v in per.values()))
        self.assertEqual(per["signature"]["reason"], "run label SECOND_IMPLEMENTATION")

    def test_runner_authored_must_be_strings(self):
        s = scope()
        s["runner_authored"] = []
        validate_scope(s)
        s["runner_authored"] = ["verifier", ""]
        with self.assertRaises(ScopeError):
            validate_scope(s)

    def test_adequacy_rows_are_keyed(self):
        s = scope("toy-run")
        self.assertEqual(set(independence.per_claim(s)), {r["id"] for r in s["rows"]})

    def test_roles_and_trust_material_are_optional_nonempty_lists(self):
        s = scope()
        s["verifier_authors"] = ["someone"]
        s["trust_material"] = ["APS keys are the fixture's published test keys"]
        validate_scope(s)
        for key in ("verifier_authors", "trust_material"):
            bad = copy.deepcopy(s)
            bad[key] = []
            with self.assertRaises(ScopeError):
                validate_scope(bad)

    def test_mapping(self):
        self.assertEqual(independence.FEDERATION["SELF_RUN"], "AUTHOR_RUN")
        self.assertEqual(independence.BCR["REPRODUCTION"], "BCR-1")
        self.assertEqual(set(independence.FEDERATION), set(independence.BCR))


if __name__ == "__main__":
    unittest.main()
