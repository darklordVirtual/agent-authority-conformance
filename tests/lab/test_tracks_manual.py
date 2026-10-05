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
        self.assertIn("## Independence per claim", report)
        self.assertIn("**Roles:** verifier or adapter authored by tester; run operated by AAC tests", report)
        self.assertIn("BCR-3 at most", report)


if __name__ == "__main__":
    unittest.main()


class PhaseTest(LabTest):
    """Pre-run statements stay pre-run; post-run review stays post-run (#177: a post-run
    producer review is not prior authorisation)."""

    def test_scope_and_authorisation_only_before_freeze(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        for action in ("scope_agreed", "run_authorized"):
            with self.assertRaisesRegex(GateError, "SCOPED"):
                consent.add(run, "maintainer", action, AGREE_REF, NOW)

    def test_admission_only_between_freeze_and_run(self):
        from tests.lab.helpers import prepare_run
        run = prepare_run(self, "toy-verification-run", "toy-receipts")
        with self.assertRaisesRegex(GateError, "FROZEN"):
            admit(run, "within")

    def test_review_ack_only_after_delivery(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        with self.assertRaisesRegex(GateError, "SHARED_PRIVATE"):
            consent.add(run, "maintainer", "review_ack", AGREE_REF, NOW)

    def test_withdrawn_consent_stops_freeze_and_run(self):
        from tests.lab.helpers import agree, prepare_run
        run = prepare_run(self, "toy-verification-run", "toy-receipts")
        lifecycle.pin(run)
        agree(run)
        consent.add(run, "tester", "withdrawn", AGREE_REF, NOW)
        with self.assertRaisesRegex(GateError, "withdrew"):
            lifecycle.freeze(run, NOW)
        run2 = frozen_run(self, "toy-run", "toy-subject")
        consent.add(run2, "tester", "withdrawn", AGREE_REF, NOW)
        with self.assertRaisesRegex(GateError, "withdrew"):
            runner.run(run2, NOW)


class NegativeControlTest(LabTest):
    """Declared negative controls show the procedure can fail; they are evaluated only
    after every result exists and are never passed to a check."""

    def run_with_controls(self, controls):
        from conformance.lab.canonical import write_json
        from tests.lab.helpers import agree, prepare_run
        run = prepare_run(self, "toy-verification-run", "toy-receipts")
        scope = read_json(run / "SCOPE.json")
        for claim in scope["claims"]:
            if claim["id"] in controls:
                claim["negative_controls"] = controls[claim["id"]]
        write_json(run / "SCOPE.json", scope)
        lifecycle.pin(run)
        agree(run)
        lifecycle.freeze(run, NOW)
        from tests.lab.helpers import PLAN_REF, admit_all
        lifecycle.freeze(run, NOW, PLAN_REF)
        admit_all(run)
        runner.run(run, NOW)
        return run

    def test_discriminated_and_not_discriminated_are_reported_separately(self):
        # over.json exceeds the cap (CONTRADICTED: discriminated); within.json is ESTABLISHED
        # for cap_compliance, so declaring it a negative control shows a control that failed.
        run = self.run_with_controls({"cap_compliance": ["over", "within"]})
        rows = {(c["claim"], c["input"]): c for c in read_json(run / "results" / "controls.json")["controls"]}
        self.assertEqual(rows[("cap_compliance", "over")]["discriminated"], True)
        self.assertEqual(rows[("cap_compliance", "within")]["discriminated"], False)
        lifecycle.package(run, NOW)
        report = (run / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("## Negative controls", report)
        self.assertIn("did not discriminate", report)
        outcome, details = rerun(run)
        self.assertEqual(outcome, "REPRODUCED", details)

    def test_control_must_be_a_claim_input(self):
        from conformance.lab.errors import ScopeError
        from conformance.lab.scope import validate_scope
        scope = read_json(self.copy_fixture("toy-verification-run", self.tmp / "x") / "SCOPE.json")
        scope["claims"][2]["negative_controls"] = ["over"]  # signature reads only "within"
        with self.assertRaisesRegex(ScopeError, "negative_controls"):
            validate_scope(scope)


class ReviewRegressionTest(LabTest):
    def test_mixed_case_parties_can_agree(self):
        from conformance.lab.canonical import write_json
        from tests.lab.helpers import AGREE_REF, PLAN_REF, prepare_run
        run = prepare_run(self, "toy-verification-run", "toy-receipts")
        scope = read_json(run / "SCOPE.json")
        scope["agreement_parties"] = ["darklordVirtual"]
        write_json(run / "SCOPE.json", scope)
        lifecycle.pin(run)
        for action in ("scope_agreed", "run_authorized"):
            consent.add(run, "@DarklordVirtual", action, AGREE_REF, NOW)
        lifecycle.freeze(run, NOW)
        lifecycle.freeze(run, NOW, PLAN_REF)

    def test_admission_only_by_runner_party_or_subject_maintainer(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts", admit=False)
        with self.assertRaisesRegex(GateError, "admission"):
            consent.add(run, "stranger", "admission", AGREE_REF, NOW, input="within", decision="ADMITTED",
                        rationale="r")
        consent.add(run, "maintainer", "admission", AGREE_REF, NOW, input="within", decision="ADMITTED",
                    rationale="subject maintainer")

    def test_capture_only_before_the_run_completes_and_redacts_errors(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from conformance.lab.__main__ import main
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        cfg = {"org": "x", "runs_dir": self.tmp / "runs"}
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["run", "toy-verification"], config=cfg), 0)
            lifecycle.package(run, NOW)
            before = (run / "RUN-CAPTURE.json").read_bytes()
            self.assertEqual(main(["run", "toy-verification"], config=cfg), 2)  # refused: already packaged
        self.assertEqual((run / "RUN-CAPTURE.json").read_bytes(), before)
        from conformance.lab.__main__ import _redact
        self.assertNotIn("/Users/someone/", _redact("cannot read /Users/someone/x.json"))
