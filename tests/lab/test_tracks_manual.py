"""Manual track: admission before inference, conditions carried with their claims."""

import unittest

from conformance.lab import consent, lifecycle, runner
from conformance.lab.canonical import read_json
from conformance.lab.errors import GateError, PackageError
from conformance.lab.rerun import rerun
from tests.lab.helpers import AGREE_REF, NOW, LabTest, frozen_run


def admit(run, input_id, decision="ADMITTED"):
    consent.add(run, "tester", "admission", AGREE_REF, NOW, input=input_id, decision=decision,
                rationale=f"{decision.lower()} in test")


class AdmissionTest(LabTest):
    def setUp(self):
        super().setUp()
        self.run = frozen_run(self, "toy-verification-run", "toy-receipts", admit=False)

    def test_run_refused_without_admission(self):
        admit(self.run, "within")
        with self.assertRaisesRegex(GateError, "over"):
            runner.run(self.run, NOW)

    def test_not_admitted_and_unknown_are_non_verdicts(self):
        admit(self.run, "within")
        admit(self.run, "over", "ADMITTED")
        admit(self.run, "over", "UNKNOWN")  # the latest decision counts
        runner.run(self.run, NOW)
        records = read_json(self.run / "results" / "claims.json")["records"]
        over = [r for r in records if r["input"] == "over"]
        self.assertTrue(over)
        for r in over:
            self.assertEqual((r["execution"], r["result"], r["verifier_error"]["code"]),
                             ("NOT_ADMITTED", None, "not_admitted"))
        self.assertTrue(all(r["result"] for r in records if r["input"] == "within"))
        from tests.lab.test_schema_agreement import validator
        validator("claim-results").validate(read_json(self.run / "results" / "claims.json"))
        admission = read_json(self.run / "results" / "admission.json")["inputs"]
        self.assertEqual((admission["over"]["decision"], admission["within"]["decision"]), ("UNKNOWN", "ADMITTED"))

    def test_rerun_reproduces_non_verdicts(self):
        admit(self.run, "within")
        admit(self.run, "over", "NOT_ADMITTED")
        runner.run(self.run, NOW)
        lifecycle.package(self.run, NOW)
        outcome, details = rerun(self.run)
        self.assertEqual(outcome, "REPRODUCED", details)

    def test_adequacy_needs_no_admission(self):
        run = frozen_run(self, admit=False)
        runner.run(run, NOW)  # adequacy rows have no inputs to admit


class ConditionTest(LabTest):
    def built(self, claims):
        run = frozen_run(self, "toy-verification-run", "toy-receipts",
                         conditions=[{"text": "under published test keys only", "claims": claims}])
        consent.add(run, "maintainer", "review_ack", AGREE_REF, NOW)  # satisfies no gate
        runner.run(run, NOW)
        return run

    def test_unknown_claim_refused_at_package(self):
        run = self.built(["nope"])
        with self.assertRaisesRegex(PackageError, "nope"):
            lifecycle.package(run, NOW)

    def test_condition_rendered_under_its_claim(self):
        run = self.built(["exact_call"])
        lifecycle.package(run, NOW)
        report = (run / "REPORT.md").read_text(encoding="utf-8")
        section = report.split("## Claim conditions", 1)[1]
        self.assertIn("exact_call", section)
        self.assertIn("under published test keys only", section)
        self.assertIn("tester", section)
        self.assertNotIn("cap_compliance", section.split("##", 1)[0])


if __name__ == "__main__":
    unittest.main()
