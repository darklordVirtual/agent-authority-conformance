import contextlib
import copy
import io
import json
from pathlib import Path
import unittest

from conformance.adapter import validate_manifest
from conformance.validation import load_validator
from conformance.observed_effect_vantage import (
    VantageResult,
    evaluate_observation_vantage,
    evaluate_observation_vantage_r2,
    main,
)

ADAPTER = Path(__file__).parents[1] / "adapters" / "rfc189-observed-effect-oe08-vantage-v1" / "adapter.json"

FIXTURE = (
    Path(__file__).parents[1]
    / "interop"
    / "fixtures"
    / "rfc189-oe-08-self-vantage.json"
)


def load_case():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ObservedEffectVantageTests(unittest.TestCase):
    def test_oe08_self_vantage_is_not_established(self):
        case = load_case()
        verdict = evaluate_observation_vantage(
            case["input"],
            trusted_control_domains=case["runner_trust"]["trusted_control_domains"],
        )
        self.assertEqual(verdict.as_dict(), case["expected"])

    def test_declared_independence_never_upgrades_self_vantage(self):
        record = copy.deepcopy(load_case()["input"])
        record["declared_independence"] = True
        record["control_domain"] = "nominally-external-domain"
        verdict = evaluate_observation_vantage(
            record, trusted_control_domains={"nominally-external-domain"}
        )
        self.assertEqual(verdict.result, VantageResult.NOT_ESTABLISHED)
        self.assertEqual(verdict.unmet_obligation, "observation_vantage")
        self.assertEqual(
            verdict.reason, "authoritative-vantage-not-independent"
        )

    def test_independent_vantage_requires_runner_owned_trust(self):
        record = {
            "observer_id": "verifier",
            "observed_party": "agent",
            "control_domain": "verifier-domain",
            "observed_control_domain": "agent-domain",
            "can_observed_party_forge": False,
            "can_observed_party_suppress": False,
            "declared_independence": True,
        }
        without_trust = evaluate_observation_vantage(record)
        with_trust = evaluate_observation_vantage(
            record, trusted_control_domains={"verifier-domain"}
        )
        self.assertEqual(without_trust.result, VantageResult.NOT_ESTABLISHED)
        self.assertEqual(with_trust.result, VantageResult.ESTABLISHED)

    def test_shared_control_domain_is_not_independent(self):
        record = {
            "observer_id": "verifier",
            "observed_party": "agent",
            "control_domain": "shared-domain",
            "observed_control_domain": "shared-domain",
            "can_observed_party_forge": False,
            "can_observed_party_suppress": False,
        }
        verdict = evaluate_observation_vantage(
            record, trusted_control_domains={"shared-domain"}
        )
        self.assertEqual(verdict.result, VantageResult.NOT_ESTABLISHED)

    def test_forge_or_suppress_capability_blocks_independence(self):
        base = {
            "observer_id": "verifier",
            "observed_party": "agent",
            "control_domain": "verifier-domain",
            "observed_control_domain": "agent-domain",
            "can_observed_party_forge": False,
            "can_observed_party_suppress": False,
        }
        for field in ("can_observed_party_forge", "can_observed_party_suppress"):
            with self.subTest(field=field):
                record = dict(base)
                record[field] = True
                verdict = evaluate_observation_vantage(
                    record, trusted_control_domains={"verifier-domain"}
                )
                self.assertEqual(verdict.result, VantageResult.NOT_ESTABLISHED)

    def test_missing_negative_capability_facts_do_not_establish_independence(self):
        record = {
            "observer_id": "verifier",
            "observed_party": "agent",
            "control_domain": "verifier-domain",
            "observed_control_domain": "agent-domain",
        }
        verdict = evaluate_observation_vantage(
            record, trusted_control_domains={"verifier-domain"}
        )
        self.assertEqual(verdict.result, VantageResult.NOT_ESTABLISHED)
        self.assertEqual(verdict.reason, "observation-vantage-not-established")

    def test_malformed_boolean_is_non_verdict(self):
        record = copy.deepcopy(load_case()["input"])
        record["declared_independence"] = "true"
        verdict = evaluate_observation_vantage(record)
        self.assertEqual(verdict.result, VantageResult.INVALID_INPUT)
        self.assertIsNone(verdict.unmet_obligation)

    def test_expected_answer_is_separate_from_checker_input(self):
        case = load_case()
        self.assertNotIn("expected", case["input"])
        self.assertNotIn("native_expected", case["input"])

    def test_cli_rejects_non_object_case_files_as_invalid_input(self):
        import tempfile
        for document in ([], {"input": {}, "runner_trust": []}, "text"):
            with self.subTest(document=document), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "case.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = main([str(path)])
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(out.getvalue())["result"], "INVALID_INPUT")

    def test_public_source_adapter_is_schema_valid(self):
        manifest = json.loads(ADAPTER.read_text(encoding="utf-8"))
        load_validator("federation-adapter-v1.schema.json").validate(manifest)
        validate_manifest(manifest)
        self.assertEqual(
            manifest["subject"]["revision"],
            load_case()["source"]["revision"],
        )
        self.assertEqual(
            manifest["artifacts"][0]["sha256"],
            load_case()["source"]["sha256"],
        )

    def test_source_pin_is_explicit(self):
        source = load_case()["source"]
        self.assertEqual(len(source["revision"]), 40)
        self.assertEqual(len(source["sha256"]), 64)
        self.assertEqual(
            source["path"],
            "conformance/RFC-189/observed-effect/cases/"
            "RFC189-OE-08-NE-SELF-VANTAGE-CLAIMING-INDEPENDENCE.json",
        )


if __name__ == "__main__":
    unittest.main()


EXTERNAL = {
    "observer_id": "verifier", "observed_party": "agent",
    "control_domain": "verifier-domain", "observed_control_domain": "agent-domain",
    "can_observed_party_forge": False, "can_observed_party_suppress": False,
}
IDENTITY = {"verifier": {"established_outside_producer": True,
                         "producer_can_issue": False, "producer_can_revoke": False}}
CUSTODY = {"verifier": {"producer_can_access_signing_key": False}}


class ObservedEffectVantageRevision2Tests(unittest.TestCase):
    """Profile revision 2 (profiles/AACP-OBSERVED-EFFECT-VANTAGE-2.md)."""

    def r2(self, record=EXTERNAL, identity=IDENTITY, custody=CUSTODY):
        return evaluate_observation_vantage_r2(
            record, trusted_control_domains={"verifier-domain"},
            observer_identity_basis=identity, observer_key_custody_basis=custody)

    def test_identity_and_custody_evidence_establish_independence(self):
        self.assertEqual(self.r2().result, VantageResult.ESTABLISHED)

    def test_distinct_labels_do_not_establish_independence(self):
        verdict = self.r2(identity=None, custody=None)
        self.assertEqual((verdict.result, verdict.unmet_obligation),
                         (VantageResult.NOT_ESTABLISHED, "observer_identity_basis"))

    def test_producer_controlled_observer_identity_blocks_independence(self):
        for field, value in (("established_outside_producer", False),
                             ("producer_can_issue", True), ("producer_can_revoke", True)):
            with self.subTest(field=field):
                identity = {"verifier": {**IDENTITY["verifier"], field: value}}
                verdict = self.r2(identity=identity)
                self.assertEqual((verdict.result, verdict.unmet_obligation),
                                 (VantageResult.NOT_ESTABLISHED, "observer_identity_basis"))

    def test_producer_accessible_signing_key_blocks_independence(self):
        for custody in ({"verifier": {"producer_can_access_signing_key": True}}, {}, None):
            with self.subTest(custody=custody):
                verdict = self.r2(custody=custody)
                self.assertEqual((verdict.result, verdict.unmet_obligation),
                                 (VantageResult.NOT_ESTABLISHED, "observer_key_custody_basis"))

    def test_basis_for_another_observer_does_not_count(self):
        verdict = self.r2(identity={"someone-else": IDENTITY["verifier"]})
        self.assertEqual(verdict.unmet_obligation, "observer_identity_basis")

    def test_revision_2_keeps_every_revision_1_refusal(self):
        case = load_case()
        verdict = evaluate_observation_vantage_r2(
            case["input"], trusted_control_domains=case["runner_trust"]["trusted_control_domains"],
            observer_identity_basis=IDENTITY, observer_key_custody_basis=CUSTODY)
        self.assertEqual(verdict.as_dict(), case["expected"])

    def test_revision_1_is_frozen_as_published(self):
        """Revision 1 still establishes on labels and explicit facts alone; that
        is the gap revision 2 closes, and records under revision 1 keep it."""
        verdict = evaluate_observation_vantage(EXTERNAL, trusted_control_domains={"verifier-domain"})
        self.assertEqual(verdict.result, VantageResult.ESTABLISHED)

    def test_cli_applies_revision_2_on_request(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps({"input": EXTERNAL, "runner_trust": {
                "trusted_control_domains": ["verifier-domain"]}}), encoding="utf-8")
            for revision, expected in (("1", "ESTABLISHED"), ("2", "NOT_ESTABLISHED")):
                with self.subTest(revision=revision):
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        code = main(["--profile-revision", revision, str(path)])
                    self.assertEqual((code, json.loads(out.getvalue())["result"]), (0, expected))
