"""Self-service track: a producer's standing offer replaces per-run human gates."""

import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from unittest import mock

from conformance.lab import consent, lifecycle, runner, state
from conformance.lab.canonical import read_json, write_json
from conformance.lab.errors import GateError, ScopeError
from conformance.lab.scope import validate_scope
from tests.lab.helpers import (AGREE_REF, FIXTURES, NOW, OFFER_PATH, PLAN_REF, LabTest, commit_files, frozen_run,
                               offer_entry, offers_doc, self_service_run)

FAKE_GH = Path(__file__).resolve().parent / "fake_gh.py"
ORG = "Runner-Org"
LATER = "2026-10-08T12:00:00Z"   # NOW + 7 days
EARLY = "2026-10-07T11:59:59Z"   # just short of 7 days
BEFORE = "2026-09-30T12:00:00Z"  # before the share


def after_review(disagreement="HOLD"):
    return {"publication": {"mode": "PUBLIC_AFTER_REVIEW", "review_window_days": 7,
                            "unresolved_disagreement": disagreement}}


class ScopeTest(unittest.TestCase):
    def scope(self):
        return json.loads((FIXTURES / "toy-offer-run" / "SCOPE.json").read_text(encoding="utf-8"))

    def test_self_service_scope_needs_no_parties_or_approvers(self):
        validate_scope(self.scope())

    def test_self_service_rules(self):
        cases = {
            "no offer": lambda s: s.pop("offer"),
            "adequacy": lambda s: s.__setitem__("kind", "adequacy"),
            "publication given": lambda s: s.__setitem__("publication", {"approvers": ["x"], "private_first": True,
                                                                         "unreleased_citable": False}),
            "bad track": lambda s: s.__setitem__("track", "fast"),
            "bad claim ceiling": lambda s: s["claims"][0].__setitem__("claim_ceiling", {"establishes": []}),
        }
        for label, edit in cases.items():
            s = self.scope()
            edit(s)
            with self.subTest(label), self.assertRaises(ScopeError):
                validate_scope(s)

    def test_scope_without_track_is_manual_and_unchanged(self):
        s = json.loads((FIXTURES / "toy-verification-run" / "SCOPE.json").read_text(encoding="utf-8"))
        validate_scope(s)
        s.pop("publication")
        with self.assertRaises(ScopeError):
            validate_scope(s)


class SelfServiceFlowTest(LabTest):
    def setUp(self):
        super().setUp()
        self.gh_state = self.tmp / "gh.json"
        self.gh_state.write_text(json.dumps({"owners": {ORG: "Organization"}, "repos": {}, "calls": []}))
        env = {"AAC_GH": f"{shlex.quote(sys.executable)} {shlex.quote(str(FAKE_GH))}",
               "FAKE_GH_STATE": str(self.gh_state), "AAC_GIT_REMOTE_BASE": str(self.tmp / "github")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def visibility(self, run_id="toy-offer"):
        return json.loads(self.gh_state.read_text())["repos"][f"{ORG}/{run_id}"]["visibility"]

    def to_shared(self, preregister=False, **overrides):
        run, producer = self_service_run(self, **overrides)
        lifecycle.pin(run)
        if preregister:
            lifecycle.freeze(run, NOW)
            lifecycle.freeze(run, NOW, PLAN_REF)
        else:
            lifecycle.freeze(run, NOW, not_preregistered=True)
        runner.run(run, NOW)
        lifecycle.package(run, NOW)
        lifecycle.share(run, ORG, [], NOW)
        return run, producer

    def test_full_immediate_flow_without_any_consent(self):
        run, _ = self.to_shared()
        lifecycle.publish(run, NOW)
        self.assertEqual(state.load_state(run)["state"], "PUBLISHED")
        self.assertEqual(self.visibility(), "PUBLIC")
        self.assertEqual(consent.load(run), [])
        status = (run / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("self-service", status)
        self.assertIn("not reviewed and not endorsed", status)
        report = (run / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("toy-receipts-v1", report)
        self.assertIn("Preregistered: no", report)
        self.assertIn("cumulative spend", report)  # per-claim ceiling from the offer
        admission = read_json(run / "results" / "admission.json")["inputs"]
        self.assertEqual(admission["over"]["who"], "offer:toy-receipts-v1")

    def test_preregistered_flag(self):
        run, _ = self.to_shared(preregister=True)
        self.assertTrue(state.load_state(run)["preregistered"])
        self.assertIn("Preregistered: yes", (run / "REPORT.md").read_text(encoding="utf-8"))

    def test_not_preregistered_is_refused_on_manual_runs(self):
        from tests.lab.helpers import agree, prepare_run
        manual = prepare_run(self, "toy-run", "toy-subject")
        lifecycle.pin(manual)
        agree(manual)
        with self.assertRaisesRegex(GateError, "self-service"):
            lifecycle.freeze(manual, NOW, not_preregistered=True)

    def test_scope_exceeding_offer_refused_at_pin(self):
        run, _ = self_service_run(self)
        scope = read_json(run / "SCOPE.json")
        scope["claims"][0]["claim_ceiling"] = {"establishes": ["everything"], "does_not_establish": ["nothing"]}
        write_json(run / "SCOPE.json", scope)
        with self.assertRaisesRegex(ScopeError, "claim_ceiling"):
            lifecycle.pin(run)

    def test_revoked_after_pin_blocks_freeze_and_run(self):
        run, producer = self_service_run(self)
        lifecycle.pin(run)
        scope = read_json(run / "SCOPE.json")
        commit_files(producer, {OFFER_PATH: offers_doc(offer_entry(
            scope["offer"]["repo"], scope["subjects"][0]["commit"], revoked=True))})
        with self.assertRaisesRegex(GateError, "revoked"):
            lifecycle.freeze(run, NOW, not_preregistered=True)

    def test_revoked_after_freeze_blocks_run(self):
        run, producer = self_service_run(self)
        lifecycle.pin(run)
        lifecycle.freeze(run, NOW, not_preregistered=True)
        commit_files(producer, {}, remove=[OFFER_PATH])
        with self.assertRaisesRegex(GateError, "withdrawn"):
            runner.run(run, NOW)
        self.assertEqual(state.load_state(run)["state"], "FROZEN")

    def test_after_review_window(self):
        run, _ = self.to_shared(**after_review())
        with self.assertRaisesRegex(GateError, "window"):
            lifecycle.publish(run, EARLY)
        lifecycle.publish(run, LATER)
        status = (run / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("No producer response within the 7-day window", status)
        self.assertIn("not agreement", status)

    def test_window_with_clock_before_share_refused(self):
        run, _ = self.to_shared(**after_review())
        with self.assertRaisesRegex(GateError, "before"):
            lifecycle.publish(run, BEFORE)

    def test_decline_with_hold_blocks_and_allows_withhold(self):
        run, _ = self.to_shared(**after_review("HOLD"))
        consent.add(run, "maintainer", "publication_declined", AGREE_REF, NOW)
        with self.assertRaisesRegex(GateError, "HOLD"):
            lifecycle.publish(run, LATER)
        lifecycle.withhold(run, LATER)
        self.assertEqual(state.load_state(run)["state"], "WITHHELD")
        self.assertEqual(self.visibility(), "PRIVATE")

    def test_decline_with_disagreement_is_published_with_it(self):
        run, _ = self.to_shared(**after_review("PUBLISH_WITH_DISAGREEMENT"))
        lifecycle.review(run, "maintainer", "corrections", AGREE_REF, NOW)
        consent.add(run, "maintainer", "publication_declined", AGREE_REF, NOW)
        lifecycle.publish(run, LATER)
        status = (run / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("declined publication", status)
        self.assertIn(AGREE_REF, status)
        self.assertNotIn("No producer response", status)

    def test_decline_by_non_maintainer_is_ignored(self):
        run, _ = self.to_shared(**after_review("HOLD"))
        consent.add(run, "someone-else", "publication_declined", AGREE_REF, NOW)
        lifecycle.publish(run, LATER)
        self.assertEqual(state.load_state(run)["state"], "PUBLISHED")

    def test_offer_revoked_before_publish_blocks_publish(self):
        run, producer = self.to_shared()
        scope = read_json(run / "SCOPE.json")
        commit_files(producer, {OFFER_PATH: offers_doc(offer_entry(
            scope["offer"]["repo"], scope["subjects"][0]["commit"], revoked=True))})
        with self.assertRaisesRegex(GateError, "revoked"):
            lifecycle.publish(run, NOW)

    def test_manual_publish_unchanged(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        runner.run(run, NOW)
        lifecycle.package(run, NOW)
        lifecycle.share(run, ORG, [], NOW)
        with self.assertRaisesRegex(GateError, "REVIEWED"):
            lifecycle.publish(run, NOW)


if __name__ == "__main__":
    unittest.main()
