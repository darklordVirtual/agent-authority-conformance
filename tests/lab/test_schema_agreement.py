"""The stdlib validator and the published JSON Schemas must agree on fixtures."""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from conformance.lab.errors import ScopeError
from conformance.lab.scope import validate_scope
from tests.lab.helpers import FIXTURES

SCHEMAS = Path(__file__).resolve().parents[2] / "schema" / "lab"


def validator(name):
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def stdlib_valid(scope):
    try:
        validate_scope(scope)
        return True
    except ScopeError:
        return False


class SchemaAgreementTest(unittest.TestCase):
    def variants(self):
        base = json.loads((FIXTURES / "toy-run" / "SCOPE.json").read_text(encoding="utf-8"))
        ver = json.loads((FIXTURES / "toy-verification-run" / "SCOPE.json").read_text(encoding="utf-8"))
        offer_run = json.loads((FIXTURES / "toy-offer-run" / "SCOPE.json").read_text(encoding="utf-8"))
        yield "adequacy", base
        yield "verification", ver
        yield "self-service", offer_run
        for label, edit in {
            "self-service adequacy": lambda s: s.__setitem__("kind", "adequacy"),
            "self-service with publication": lambda s: s.__setitem__("publication", ver["publication"]),
            "self-service without offer": lambda s: s.pop("offer"),
        }.items():
            scope = copy.deepcopy(offer_run)
            edit(scope)
            yield label, scope
        manual_without_parties = copy.deepcopy(ver)
        manual_without_parties.pop("agreement_parties")
        yield "manual without parties", manual_without_parties
        boundary = copy.deepcopy(offer_run)
        boundary.pop("offer")
        boundary["public_boundary"] = {
            "repo": boundary["subjects"][0]["repo"], "commit": "a" * 40, "path": "docs/BOUNDARY.md",
            "sha256": "b" * 64, "procedure_ref": "docs/BOUNDARY.md#procedure",
            "claims_ref": "docs/BOUNDARY.md#claims", "classification_ref": "docs/BOUNDARY.md#classification"}
        yield "public boundary", boundary
        two_revisions = copy.deepcopy(boundary)
        two_revisions["subjects"].append({**two_revisions["subjects"][0], "commit": "c" * 40})
        yield "public boundary, two revisions of its repository", two_revisions
        two_offer_subjects = copy.deepcopy(offer_run)
        two_offer_subjects["subjects"].append({**two_offer_subjects["subjects"][0], "commit": "c" * 40})
        yield "offer with two subjects", two_offer_subjects
        bad_boundary_path = copy.deepcopy(boundary)
        bad_boundary_path["public_boundary"]["path"] = "../escape.md"
        yield "public boundary path escapes", bad_boundary_path
        probe = {"id": "p1", "text": "probed", "class": "BINDING_GAP", "check": "m:f", "inputs": ["within"],
                 "reads_fields": ["x"], "runner_assessment": {"level": "low", "rationale": "r"},
                 "source_locators": [{"subject": 0, "path": "receipts/within.json", "lines": "1-3", "note": "n"}]}
        challenge = {"ref": "https://example.invalid/c", "by": "p", "asked": ["recompute"],
                     "requests_endorsement": False}
        rich = copy.deepcopy(ver)
        rich["probes"] = [probe]
        rich["challenge"] = challenge
        rich["inputs"][0]["format"] = "bytes"
        yield "probes, challenge and bytes input", rich
        for label, edit in {
            "probe bad class": lambda s: s["probes"][0].__setitem__("class", "SEVERE"),
            "probe bad level": lambda s: s["probes"][0]["runner_assessment"].__setitem__("level", "critical"),
            "probe bad lines": lambda s: s["probes"][0]["source_locators"][0].__setitem__("lines", "a-b"),
            "challenge http": lambda s: s["challenge"].__setitem__("ref", "http://x"),
            "challenge extra key": lambda s: s["challenge"].__setitem__("consent", True),
            "bad input format": lambda s: s["inputs"][0].__setitem__("format", "yaml"),
        }.items():
            scope = copy.deepcopy(rich)
            edit(scope)
            yield label, scope
        adequacy_with_probes = copy.deepcopy(base)
        adequacy_with_probes["probes"] = [probe]
        yield "adequacy with probes", adequacy_with_probes
        edits = {
            "no ceiling": lambda s: s.pop("claim_ceiling"),
            "score key": lambda s: s.__setitem__("score", 3),
            "public first": lambda s: s["publication"].__setitem__("private_first", False),
            "short commit": lambda s: s["subjects"][0].__setitem__("commit", "abc"),
            "bad kind": lambda s: s.__setitem__("kind", "ranking"),
            "no approvers": lambda s: s["publication"].__setitem__("approvers", []),
            "absolute path": lambda s: s["subjects"][0].__setitem__("paths", ["/etc"]),
            "no rows": lambda s: s.pop("rows"),
        }
        for label, edit in edits.items():
            scope = copy.deepcopy(base)
            edit(scope)
            yield label, scope
        scope = copy.deepcopy(ver)
        scope.pop("independence_statement")
        yield "independent without statement", scope

    def test_scope_schema_agrees_with_stdlib(self):
        schema = validator("scope")
        for label, scope in self.variants():
            with self.subTest(variant=label):
                self.assertEqual(schema.is_valid(scope), stdlib_valid(scope))

    def test_fault_fixtures_match_schema(self):
        schema = validator("faults")
        run = FIXTURES / "toy-run"
        for path in [run / "faults" / "known.json", *sorted((run / "controls").glob("*.json"))]:
            with self.subTest(path=path.name):
                schema.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_consent_events_match_schema(self):
        import tempfile
        from conformance.lab import consent
        from tests.lab.helpers import AGREE_REF, NOW
        with tempfile.TemporaryDirectory() as tmp:
            consent.add(tmp, "a", "scope_agreed", AGREE_REF, NOW,
                        conditions=[{"text": "test keys only", "claims": ["c1"]}])
            consent.add(tmp, "a", "admission", AGREE_REF, NOW, drafted_by="agent:x", ai_assisted=True,
                        input="i1", decision="UNKNOWN", rationale="provenance open")
            consent.add(tmp, "b", "review_ack", AGREE_REF, NOW, recorded_by="op")
            doc = json.loads((Path(tmp) / consent.FILE).read_text(encoding="utf-8"))
        schema = validator("consent")
        schema.validate(doc)
        bad = json.loads(json.dumps(doc))
        bad["events"][1].pop("decision")
        self.assertFalse(schema.is_valid(bad))
        bad = json.loads(json.dumps(doc))
        bad["events"][2]["conditions"] = [{"text": "x", "claims": ["c1"]}]
        self.assertFalse(schema.is_valid(bad))

    def test_offers_schema_and_validator_agree(self):
        from conformance.lab import offer
        from tests.lab.helpers import offer_entry, offers_doc
        schema = validator("offers")
        example = json.loads((Path(__file__).resolve().parents[2] / "templates" / "offers"
                              / "aacp-offers.example.json").read_text(encoding="utf-8"))
        good = json.loads(offers_doc(offer_entry("https://example.invalid/p", "a" * 40)))
        for doc in (example, good):
            schema.validate(doc)
            offer.validate_offers(doc)
        for overrides in ({"kinds": ["adequacy"]}, {"executes_producer_code": True}, {"expires": "soon"},
                          {"publication": {"mode": "PUBLIC_AFTER_REVIEW", "review_window_days": None,
                                           "unresolved_disagreement": "HOLD"}}):
            bad = json.loads(offers_doc(offer_entry("https://example.invalid/p", "a" * 40, **overrides)))
            self.assertFalse(schema.is_valid(bad), overrides)
            with self.assertRaises(ScopeError):
                offer.validate_offers(bad)

    def test_remaining_schemas_are_valid_schemas(self):
        for name in ("consent", "claim-results", "row-result", "probe-results"):
            validator(name)


if __name__ == "__main__":
    unittest.main()
