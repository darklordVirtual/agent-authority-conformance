import json
from pathlib import Path
import unittest

from conformance.validation import validate_assessment


ROOT = Path(__file__).parents[1]
ADVERSARIAL = ROOT / "tests" / "adversarial"


class AdversarialAssessmentTests(unittest.TestCase):
    def test_each_property_has_pass_fail_and_untested_fixture(self):
        assessments = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in ADVERSARIAL.glob("assessment-*.json")
        }
        self.assertEqual(set(assessments), {"assessment-pass", "assessment-fail", "assessment-untested"})
        for document in assessments.values():
            validate_assessment(document)
        statuses = {
            row["id"]: {document["properties"][index]["status"] for document in assessments.values()}
            for index, row in enumerate(assessments["assessment-pass"]["properties"])
        }
        for property_id, property_statuses in statuses.items():
            with self.subTest(property_id=property_id):
                self.assertEqual(property_statuses, {"PASS", "FAIL", "UNTESTED"})

    def test_pass_evidence_is_reproducible(self):
        document = json.loads((ADVERSARIAL / "assessment-pass.json").read_text(encoding="utf-8"))
        for row in document["properties"]:
            with self.subTest(property_id=row["id"]):
                self.assertEqual(row["evidence_tier"], "RESOLVED")
                self.assertTrue(row["evidence"])
                for evidence in row["evidence"]:
                    self.assertEqual(evidence["revision"], document["revision"])
                    self.assertTrue(evidence.get("command"))
                    self.assertIn("test_adversarial", evidence["reference"])

    def test_cross_scenarios_have_known_expected_results(self):
        document = json.loads((ADVERSARIAL / "cross-scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(document["revision"], "adversarial-fixtures-v1")
        self.assertEqual({scenario["expected"] for scenario in document["scenarios"]}, {"FAIL"})
        self.assertEqual({scenario["failure_mode"] for scenario in document["scenarios"]}, {"bypass", "TOCTOU", "partial-effect"})


if __name__ == "__main__":
    unittest.main()