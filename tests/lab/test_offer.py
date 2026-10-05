"""Producer-owned open verification offers (self-service track)."""

import copy
import json
import unittest

from conformance.lab import offer
from conformance.lab.errors import GateError, PinError, ScopeError
from tests.lab.helpers import (FIXTURES, NOW, OFFER_PATH, LabTest, commit_files, offer_entry, offers_doc,
                               producer_with_offer)

REPO, COMMIT = "https://example.invalid/p", "a" * 40


def doc(*entries):
    return json.loads(offers_doc(*(entries or [offer_entry(REPO, COMMIT)])))


class ValidateTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(offer.find(offer.validate_offers(doc()), "toy-receipts-v1")["offer_id"], "toy-receipts-v1")

    def test_missing_offer_id(self):
        with self.assertRaisesRegex(ScopeError, "nope"):
            offer.find(offer.validate_offers(doc()), "nope")

    def test_duplicate_offer_id_refused(self):
        with self.assertRaisesRegex(ScopeError, "duplicate"):
            offer.validate_offers(doc(offer_entry(REPO, COMMIT), offer_entry(REPO, COMMIT)))

    def test_adequacy_kind_or_producer_code_refused(self):
        for overrides, text in (({"kinds": ["verification", "adequacy"]}, "kinds"),
                                ({"executes_producer_code": True}, "executes_producer_code")):
            with self.subTest(text), self.assertRaisesRegex(ScopeError, text):
                offer.validate_offers(doc(offer_entry(REPO, COMMIT, **overrides)))

    def test_after_review_needs_window(self):
        pub = {"mode": "PUBLIC_AFTER_REVIEW", "review_window_days": None, "unresolved_disagreement": "HOLD"}
        with self.assertRaisesRegex(ScopeError, "review_window_days"):
            offer.validate_offers(doc(offer_entry(REPO, COMMIT, publication=pub)))
        offer.validate_offers(doc(offer_entry(REPO, COMMIT, publication={**pub, "review_window_days": 7})))

    def test_other_structural_problems(self):
        cases = {
            "private mode": {"publication": {"mode": "PRIVATE_UNTIL_APPROVED", "review_window_days": None,
                                             "unresolved_disagreement": "HOLD"}},
            "short commit": {"subject": {"repo": REPO, "commit": "abc", "paths": ["receipts"]}},
            "absolute path": {"inputs": [{"id": "x", "path": "/etc/passwd"}]},
            "bad expiry": {"expires": "soon"},
            "score": {"score": 1},
            "no ceiling": {"claims": [{"id": "c", "text": "t"}]},
            "revoked not bool": {"revoked": "no"},
        }
        for label, overrides in cases.items():
            with self.subTest(label), self.assertRaises(ScopeError):
                offer.validate_offers(doc(offer_entry(REPO, COMMIT, **overrides)))


class ScopeAgainstTest(unittest.TestCase):
    def scope(self):
        s = json.loads((FIXTURES / "toy-verification-run" / "SCOPE.json").read_text(encoding="utf-8"))
        s["subjects"][0]["repo"], s["subjects"][0]["commit"] = REPO, COMMIT
        entry = offer_entry(REPO, COMMIT)
        for claim in s["claims"]:
            claim["claim_ceiling"] = next(c["claim_ceiling"] for c in entry["claims"] if c["id"] == claim["id"])
        s["procedure"] = entry["procedure"]["id"]
        s["claims"][0]["negative_controls"] = ["over"]
        return s, entry

    def test_matching_scope(self):
        s, entry = self.scope()
        offer.check_scope_against(s, entry)

    def test_scope_mismatch_lists_every_problem(self):
        s, entry = self.scope()
        s["subjects"][0]["commit"] = "b" * 40
        s["claims"].append({**s["claims"][0], "id": "extra"})
        s["claims"][1]["claim_ceiling"] = {"establishes": ["more"], "does_not_establish": ["less"]}
        s["inputs"][0]["path"] = "receipts/other.json"
        with self.assertRaises(ScopeError) as ctx:
            offer.check_scope_against(s, entry)
        message = str(ctx.exception)
        for part in ("subject", "extra", "exact_call", "within"):
            self.assertIn(part, message)

    def test_kind_must_be_offered(self):
        s, entry = self.scope()
        s["kind"] = "adequacy"
        with self.assertRaisesRegex(ScopeError, "kind"):
            offer.check_scope_against(s, entry)


class FetchTest(LabTest):
    def test_valid_offer_round_trip(self):
        ref, subject_commit, _ = producer_with_offer(self)
        entry = offer.fetch_pinned(ref, self.tmp)
        self.assertEqual(entry["subject"]["commit"], subject_commit)

    def test_hash_mismatch_refused(self):
        ref, _, _ = producer_with_offer(self)
        with self.assertRaisesRegex(PinError, "sha256"):
            offer.fetch_pinned({**ref, "sha256": "0" * 64}, self.tmp)

    def test_tip_ok_then_revoked_removed_expired(self):
        ref, subject_commit, path = producer_with_offer(self)
        offer.check_tip(ref, NOW, self.tmp)
        entry = offer_entry(ref["repo"], subject_commit, revoked=True)
        commit_files(path, {OFFER_PATH: offers_doc(entry)})
        with self.assertRaisesRegex(GateError, "revoked"):
            offer.check_tip(ref, NOW, self.tmp)
        commit_files(path, {OFFER_PATH: offers_doc(offer_entry(ref["repo"], subject_commit, offer_id="other"))})
        with self.assertRaisesRegex(GateError, "no longer lists"):
            offer.check_tip(ref, NOW, self.tmp)
        commit_files(path, {}, remove=[OFFER_PATH])
        with self.assertRaisesRegex(GateError, "withdrawn"):
            offer.check_tip(ref, NOW, self.tmp)
        commit_files(path, {OFFER_PATH: offers_doc(offer_entry(ref["repo"], subject_commit, expires="2026-09-30"))})
        with self.assertRaisesRegex(GateError, "expired"):
            offer.check_tip(ref, NOW, self.tmp)

    def test_newer_offer_does_not_revoke_older(self):
        ref, subject_commit, path = producer_with_offer(self)
        commit_files(path, {OFFER_PATH: offers_doc(offer_entry(ref["repo"], subject_commit),
                                                   offer_entry(ref["repo"], subject_commit, offer_id="v2"))})
        offer.check_tip(ref, NOW, self.tmp)

    def test_tip_follows_default_branch(self):
        ref, subject_commit, path = producer_with_offer(self, branch="trunk")
        offer.check_tip(ref, NOW, self.tmp)
        commit_files(path, {OFFER_PATH: offers_doc(offer_entry(ref["repo"], subject_commit, revoked=True))})
        with self.assertRaisesRegex(GateError, "revoked"):
            offer.check_tip(ref, NOW, self.tmp)


if __name__ == "__main__":
    unittest.main()


class ProcedureAndIssuerTest(LabTest):
    def test_offer_needs_a_runner_owned_procedure(self):
        for bad in (None, {"id": "x", "description": "d", "verifier": "producer_reference"},
                    {"id": "", "description": "d", "verifier": "runner_owned"}):
            entry = offer_entry(REPO, COMMIT)
            if bad is None:
                entry.pop("procedure")
            else:
                entry["procedure"] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ScopeError, "procedure"):
                offer.validate_offers(doc(entry))

    def test_negative_controls_must_be_offered_inputs(self):
        entry = offer_entry(REPO, COMMIT)
        entry["claims"][0]["negative_controls"] = ["nope"]
        with self.assertRaisesRegex(ScopeError, "negative_controls"):
            offer.validate_offers(doc(entry))

    def test_offer_covers_only_its_own_repository(self):
        """An offer in one repository cannot open another project's artifacts."""
        import hashlib
        _, subject_commit = self.remote_repo("victim", {"receipts/within.json": "{}"})
        text = offers_doc(offer_entry("https://example.invalid/victim", subject_commit))
        third = self.remotes / "third-party"
        from tests.lab.helpers import make_repo
        commit = make_repo(third, {OFFER_PATH: text})
        ref = {"repo": "https://example.invalid/third-party", "commit": commit, "path": OFFER_PATH,
               "offer_id": "toy-receipts-v1", "sha256": hashlib.sha256(text.encode()).hexdigest()}
        with self.assertRaisesRegex(ScopeError, "repository that issued it"):
            offer.fetch_pinned(ref, self.tmp)


class ScopeProcedureTest(unittest.TestCase):
    scope = ScopeAgainstTest.scope

    def test_procedure_must_match(self):
        s, entry = self.scope()
        s["procedure"] = "something-else"
        with self.assertRaisesRegex(ScopeError, "procedure"):
            offer.check_scope_against(s, entry)

    def test_offered_negative_controls_cannot_be_dropped(self):
        s, entry = self.scope()
        s["claims"][0]["negative_controls"] = []
        with self.assertRaisesRegex(ScopeError, "negative control"):
            offer.check_scope_against(s, entry)
