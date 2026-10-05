"""Regression tests for findings from the branch review."""

import json
import os
import shlex
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from conformance.lab import consent, lifecycle, package, runner, state
from conformance.lab.canonical import read_json, write_json
from conformance.lab.engines.native import NativeEngine
from conformance.lab.errors import GateError, PackageError, PinError, ScopeError
from conformance.lab.faults import load_fault_set
from conformance.lab.kinds import verification
from conformance.lab.scope import validate_scope
from tests.lab.helpers import AGREE_REF, FIXTURES, NOW, LabTest, frozen_run, git

FAKE_GH = Path(__file__).resolve().parent / "fake_gh.py"
ORG = "R-research-lab"


class ConsentHardeningTest(LabTest):
    def test_tail_truncation_is_detected(self):
        state.new_state(self.tmp, NOW)
        consent.add(self.tmp, "a", "publication_approved", AGREE_REF, NOW)
        consent.add(self.tmp, "b", "publication_declined", AGREE_REF, NOW)
        path = self.tmp / consent.FILE
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["events"].pop()
        path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(GateError, "removed or rewritten"):
            consent.load(self.tmp)

    def test_handles_are_case_insensitive(self):
        consent.add(self.tmp, "@Alice", "publication_declined", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), ["alice"]), "declined")
        self.assertTrue(consent.has_all(consent.load(self.tmp), ["ALICE"], "publication_declined"))

    def test_approval_before_delivery_or_before_correction_does_not_count(self):
        consent.add(self.tmp, "a", "publication_approved", AGREE_REF, NOW)
        events = consent.load(self.tmp)
        self.assertEqual(consent.publication_status(events, ["a"], since=1), "pending")
        consent.add(self.tmp, "a", "publication_approved", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), ["a"], since=1), "approved")
        consent.add(self.tmp, "b", "factual_corrections", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), ["a"], since=1), "pending")


class InputHardeningTest(LabTest):
    def test_fault_file_must_be_relative(self):
        for bad in ("/etc/hosts", "../x.py", "a\\..\\b.py"):
            path = self.tmp / "f.json"
            path.write_text(json.dumps({"name": "n", "set": "known", "source": {"author": "a", "ref": "https://x"},
                                        "faults": [{"id": "A", "class": "c", "file": bad, "anchor": "x",
                                                    "replacement": "y"}]}), encoding="utf-8")
            with self.subTest(file=bad), self.assertRaisesRegex(ScopeError, "relative path"):
                load_fault_set(path)

    def test_subject_repo_must_be_https(self):
        scope = read_json(FIXTURES / "toy-run" / "SCOPE.json")
        scope["subjects"][0]["repo"] = "--upload-pack=touch /tmp/x"
        with self.assertRaisesRegex(ScopeError, "https"):
            validate_scope(scope)
        with self.assertRaises(PinError):
            from conformance.lab.pins import fetch
            fetch("--upload-pack=x", "a" * 40, self.tmp / "c")

    def test_type_change_counts_as_moved(self):
        tree = self.tmp / "tree"
        shutil.copytree(FIXTURES / "toy-subject", tree)
        shutil.copy(FIXTURES / "toy-run" / "adapter" / "case.py", tree / "case.py")
        row = {"id": "r", "cases": ["T3"], "command": ["python3", "-B", "case.py", "{case}"], "projection": ["status"]}
        (tree / "checker.py").write_text((tree / "checker.py").read_text().replace(
            'return {"status": "rejected", "reason": "over_cap"}', 'return {"status": 1, "reason": "over_cap"}'))
        base = NativeEngine().baseline(tree, row)
        mutation = {"id": "M", "file": "checker.py", "anchor": '{"status": 1, "reason": "over_cap"}',
                    "replacement": '{"status": 1.0, "reason": "over_cap"}'}
        self.assertEqual(NativeEngine().mutant(tree, row, mutation, base).moved, 1)

    def test_malformed_verification_input_is_invalid_input(self):
        run = self.copy_fixture("toy-verification-run", self.tmp / "run")
        receipts = self.tmp / "receipts"
        shutil.copytree(FIXTURES / "toy-receipts", receipts)
        (receipts / "receipts" / "over.json").write_text("{not json", encoding="utf-8")
        scope = read_json(run / "SCOPE.json")
        records = {(r["input"], r["claim"]): r for r in verification.execute(run, scope, {0: receipts})}
        self.assertEqual(records[("over", "cap_compliance")]["execution"], "INVALID_INPUT")
        self.assertIsNone(records[("over", "cap_compliance")]["result"])
        self.assertEqual(records[("within", "cap_compliance")]["result"], "ESTABLISHED")

    def test_leak_scan_paths_and_git_urls(self):
        (self.tmp / "a.md").write_text("see /tmp/aac-run-x/tree", encoding="utf-8")
        with self.assertRaisesRegex(PackageError, "local absolute path"):
            package.scan_for_leaks(self.tmp)
        (self.tmp / "a.md").write_text("clone git@github.com:org/repo.git", encoding="utf-8")
        package.scan_for_leaks(self.tmp)


class IntegrityTest(LabTest):
    def test_package_refuses_edited_results(self):
        run_dir = frozen_run(self)
        runner.run(run_dir, NOW)
        result = read_json(run_dir / "results" / "row1.json")
        result["mutants"][2]["outcome"] = "killed"
        write_json(run_dir / "results" / "row1.json", result)
        with self.assertRaisesRegex(PackageError, "results/ differ"):
            lifecycle.package(run_dir, NOW)

    def test_run_refuses_broken_consent(self):
        run_dir = frozen_run(self)
        doc = read_json(run_dir / consent.FILE)
        doc["events"].pop()
        write_json(run_dir / consent.FILE, doc)
        with self.assertRaises(GateError):
            runner.run(run_dir, NOW)


class ShareHardeningTest(LabTest):
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

    def test_retry_after_invite_failure(self):
        with mock.patch.dict(os.environ, {"FAKE_GH_FAIL": "permission=pull"}):
            with self.assertRaises(Exception):
                lifecycle.share(self.run_dir, ORG, ["maintainer"], NOW)
        self.assertEqual(state.load_state(self.run_dir)["state"], "PACKAGED")
        lifecycle.share(self.run_dir, ORG, ["maintainer"], NOW)
        self.assertEqual(state.load_state(self.run_dir)["state"], "SHARED_PRIVATE")

    def test_stale_remote_files_are_removed(self):
        from conformance.lab import github
        github.create_private(f"{ORG}/toy")
        stale = self.tmp / "stale"
        (stale / "old").mkdir(parents=True)
        (stale / "old" / "leftover.txt").write_text("x", encoding="utf-8")
        github.push_snapshot(stale, f"{ORG}/toy", "stale")
        lifecycle.share(self.run_dir, ORG, [], NOW)
        files = git("ls-tree", "-r", "--name-only", "main", cwd=self.remote_base / ORG / "toy.git").splitlines()
        self.assertNotIn("old/leftover.txt", files)
        self.assertIn("REPORT.md", files)

    def test_share_refuses_tampered_package(self):
        (self.run_dir / "REPORT.md").write_text("edited", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "MANIFEST"):
            lifecycle.share(self.run_dir, ORG, [], NOW)

    def test_review_by_outsider_is_refused(self):
        lifecycle.share(self.run_dir, ORG, [], NOW)
        with self.assertRaisesRegex(GateError, "not an approver"):
            lifecycle.review(self.run_dir, "bystander", "classification", AGREE_REF, NOW)

    def test_approval_given_before_share_does_not_publish(self):
        for who in ("tester", "maintainer"):
            consent.add(self.run_dir, who, "publication_approved", AGREE_REF, NOW)
        lifecycle.share(self.run_dir, ORG, [], NOW)
        lifecycle.review(self.run_dir, "Maintainer", "classification", AGREE_REF, NOW)
        with self.assertRaisesRegex(GateError, "pending"):
            lifecycle.publish(self.run_dir, NOW)


if __name__ == "__main__":
    unittest.main()
