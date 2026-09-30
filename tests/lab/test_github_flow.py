import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from unittest import mock

from conformance.lab import consent, lifecycle, runner, state
from conformance.lab.errors import GateError, GitHubError
from tests.lab.helpers import AGREE_REF, NOW, LabTest, frozen_run, git

FAKE_GH = Path(__file__).resolve().parent / "fake_gh.py"
ORG = "R-research-lab"


class GitHubFlowTest(LabTest):
    def setUp(self):
        super().setUp()
        self.gh_state = self.tmp / "gh.json"
        self.gh_state.write_text(json.dumps({"owners": {ORG: "Organization"}, "repos": {}, "calls": []}))
        self.remote_base = self.tmp / "github"
        env = {"AAC_GH": f"{shlex.quote(sys.executable)} {shlex.quote(str(FAKE_GH))}",
               "FAKE_GH_STATE": str(self.gh_state), "AAC_GIT_REMOTE_BASE": str(self.remote_base)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.run_dir = frozen_run(self)
        runner.run(self.run_dir, NOW)
        lifecycle.package(self.run_dir, NOW)

    def gh(self):
        return json.loads(self.gh_state.read_text())

    def remote_file(self, rel):
        return git("show", f"main:{rel}", cwd=self.remote_base / ORG / "toy.git")

    def test_share_refuses_user_owner(self):
        with self.assertRaisesRegex(GateError, "not an organisation"):
            lifecycle.share(self.run_dir, "someone", [], NOW)
        with self.assertRaisesRegex(GateError, "no organisation"):
            lifecycle.share(self.run_dir, None, [], NOW)
        self.assertEqual(state.load_state(self.run_dir)["state"], "PACKAGED")

    def test_share_creates_private_repo_and_invites_read_only(self):
        full = lifecycle.share(self.run_dir, ORG, ["maintainer"], NOW)
        self.assertEqual(full, f"{ORG}/toy")
        repo = self.gh()["repos"][full]
        self.assertEqual(repo["visibility"], "PRIVATE")
        self.assertEqual(repo["collaborators"], {"maintainer": "pull"})
        self.assertIn("PRIVATE", self.remote_file("STATUS.md"))
        self.assertIn("SELF_RUN", self.remote_file("REPORT.md"))
        with self.assertRaises(Exception):
            self.remote_file(".local/anything")
        doc = state.load_state(self.run_dir)
        self.assertEqual((doc["state"], doc["repository"]), ("SHARED_PRIVATE", full))

    def test_gh_failure_leaves_state_unchanged(self):
        with mock.patch.dict(os.environ, {"FAKE_GH_FAIL": "create"}):
            with self.assertRaises(GitHubError):
                lifecycle.share(self.run_dir, ORG, [], NOW)
        self.assertEqual(state.load_state(self.run_dir)["state"], "PACKAGED")
        lifecycle.share(self.run_dir, ORG, [], NOW)  # retry works
        self.assertEqual(state.load_state(self.run_dir)["state"], "SHARED_PRIVATE")

    def shared_and_reviewed(self):
        lifecycle.share(self.run_dir, ORG, ["maintainer"], NOW)
        lifecycle.review(self.run_dir, "maintainer", "classification", AGREE_REF, NOW)

    def test_review_records_addendum(self):
        self.shared_and_reviewed()
        self.assertEqual(state.load_state(self.run_dir)["state"], "REVIEWED")
        self.assertIn("survivor_classification by maintainer", (self.run_dir / "REVIEW.md").read_text())

    def test_publish_requires_every_approver(self):
        self.shared_and_reviewed()
        consent.add(self.run_dir, "tester", "publication_approved", AGREE_REF, NOW)
        with self.assertRaisesRegex(GateError, "pending"):
            lifecycle.publish(self.run_dir, NOW)
        self.assertEqual(self.gh()["repos"][f"{ORG}/toy"]["visibility"], "PRIVATE")
        self.assertIn("PRIVATE", (self.run_dir / "STATUS.md").read_text())

    def test_publish_after_all_approvals(self):
        self.shared_and_reviewed()
        for who in ("tester", "maintainer"):
            consent.add(self.run_dir, who, "publication_approved", AGREE_REF, NOW)
        lifecycle.publish(self.run_dir, NOW)
        self.assertEqual(self.gh()["repos"][f"{ORG}/toy"]["visibility"], "PUBLIC")
        self.assertIn("PUBLISHED", self.remote_file("STATUS.md"))
        self.assertEqual(state.load_state(self.run_dir)["state"], "PUBLISHED")
        # Results are untouched by the publication commit.
        log = git("log", "--format=%s", "main", cwd=self.remote_base / ORG / "toy.git").splitlines()
        self.assertEqual(log, ["Record publication approval", "Private delivery of toy"])

    def test_decline_blocks_publish_and_allows_withhold(self):
        self.shared_and_reviewed()
        consent.add(self.run_dir, "tester", "publication_approved", AGREE_REF, NOW)
        consent.add(self.run_dir, "maintainer", "publication_declined", AGREE_REF, NOW)
        with self.assertRaisesRegex(GateError, "declined"):
            lifecycle.publish(self.run_dir, NOW)
        lifecycle.withhold(self.run_dir, NOW)
        self.assertEqual(state.load_state(self.run_dir)["state"], "WITHHELD")
        self.assertIn("WITHHELD", self.remote_file("STATUS.md"))
        self.assertEqual(self.gh()["repos"][f"{ORG}/toy"]["visibility"], "PRIVATE")

    def test_withhold_requires_a_decline(self):
        self.shared_and_reviewed()
        with self.assertRaisesRegex(GateError, "publication_declined"):
            lifecycle.withhold(self.run_dir, NOW)


if __name__ == "__main__":
    unittest.main()
