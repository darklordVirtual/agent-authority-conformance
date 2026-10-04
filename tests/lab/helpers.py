"""Shared test scaffolding. Every test runs in a temp dir whose name has a space."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = "2026-10-01T12:00:00Z"
AGREE_REF = "https://example.invalid/issues/1#agree"
PLAN_REF = "https://example.invalid/issues/1#plan"
REMOTE_PREFIX = "https://example.invalid/"


def git(*args, cwd):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def make_repo(root, files, branch="main"):
    """Create a git repository with files ({relpath: str|bytes}); return its commit."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    git("init", "--quiet", "-b", branch, cwd=root)
    return commit_files(root, files)


def commit_files(root, files, remove=()):
    """Write files and remove paths in an existing repository; commit and return the commit."""
    root = Path(root)
    for rel in remove:
        (root / rel).unlink()
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    git("add", "-A", cwd=root)
    git("commit", "--quiet", "-m", "fixture", cwd=root)
    return git("rev-parse", "HEAD", cwd=root)


def fixture_files(name):
    base = FIXTURES / name
    return {p.relative_to(base).as_posix(): p.read_bytes()
            for p in sorted(base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


class LabTest(unittest.TestCase):
    """Temp dir with a space, git identity, and https://example.invalid/<name>
    rewritten to local repositories under self.remotes."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="aac lab ")
        self.tmp = Path(self._tmp.name)
        self.remotes = self.tmp / "remotes"
        self.remotes.mkdir()
        env = {
            "GIT_AUTHOR_NAME": "lab test", "GIT_AUTHOR_EMAIL": "lab-test@example.invalid",
            "GIT_COMMITTER_NAME": "lab test", "GIT_COMMITTER_EMAIL": "lab-test@example.invalid",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{self.remotes.as_posix()}/.insteadOf",
            "GIT_CONFIG_VALUE_0": REMOTE_PREFIX,
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self._tmp.cleanup()

    def remote_repo(self, name, files, branch="main"):
        """Create a local repository reachable as https://example.invalid/<name>."""
        commit = make_repo(self.remotes / name, files, branch)
        return REMOTE_PREFIX + name, commit

    def copy_fixture(self, name, dest):
        shutil.copytree(FIXTURES / name, dest, ignore=shutil.ignore_patterns("__pycache__"))
        return Path(dest)


def prepare_run(test, fixture="toy-run", subject="toy-subject"):
    """Copy a run fixture into test.tmp/runs/<run_id>, point it at a local subject
    repository, and initialise empty consent and SCOPED state. Returns run_dir."""
    from conformance.lab import consent, state
    from conformance.lab.canonical import read_json, write_json

    _, commit = test.remote_repo(subject, fixture_files(subject))
    scope = read_json(FIXTURES / fixture / "SCOPE.json")
    run_dir = test.copy_fixture(fixture, test.tmp / "runs" / scope["run_id"])
    for s in scope["subjects"]:
        s["commit"] = commit
    write_json(run_dir / "SCOPE.json", scope)
    write_json(run_dir / consent.FILE, {"events": []})
    state.new_state(run_dir, NOW)
    return run_dir


def agree(run_dir, who="tester"):
    from conformance.lab import consent
    for action in ("scope_agreed", "run_authorized"):
        consent.add(run_dir, who, action, AGREE_REF, NOW)


def admit_all(run_dir, who="tester", decision="ADMITTED"):
    """Record an admission decision for every input of a verification run."""
    from conformance.lab import consent
    from conformance.lab.canonical import read_json
    scope = read_json(Path(run_dir) / "SCOPE.json")
    for item in scope.get("inputs", []):
        consent.add(run_dir, who, "admission", AGREE_REF, NOW, input=item["id"], decision=decision,
                    rationale="test fixture admitted")


def frozen_run(test, fixture="toy-run", subject="toy-subject", admit=True, conditions=None):
    from conformance.lab import consent, lifecycle
    run_dir = prepare_run(test, fixture, subject)
    lifecycle.pin(run_dir)
    if conditions:
        consent.add(run_dir, "tester", "scope_agreed", AGREE_REF, NOW, conditions=conditions)
    agree(run_dir)
    lifecycle.freeze(run_dir, NOW)
    lifecycle.freeze(run_dir, NOW, PLAN_REF)
    if admit:
        admit_all(run_dir)
    return run_dir


OFFER_PATH = "aacp-offers.json"


def offer_entry(repo, commit, **overrides):
    """An open verification offer over the toy-receipts subject at `commit`."""
    entry = {
        "offer_id": "toy-receipts-v1", "revoked": False, "expires": "2099-01-01",
        "producer": {"project": "toy-receipts", "maintainers": ["maintainer"]},
        "subject": {"repo": repo, "commit": commit, "paths": ["receipts"]},
        "inputs": [{"id": "within", "path": "receipts/within.json"},
                   {"id": "over", "path": "receipts/over.json"}],
        "claims": [
            {"id": "cap_compliance", "text": "The observed value is within the delegated cap.",
             "claim_ceiling": {"establishes": ["numeric comparison with the cap"],
                               "does_not_establish": ["units", "cumulative spend"]}},
            {"id": "exact_call", "text": "The observed value equals the authorized exact call.",
             "claim_ceiling": {"establishes": ["value comparison"], "does_not_establish": ["live execution"]}},
            {"id": "signature", "text": "The receipt signature verifies under a pinned key.",
             "claim_ceiling": {"establishes": ["fixture signature"], "does_not_establish": ["key control"]}},
        ],
        "kinds": ["verification"], "executes_producer_code": False,
        "publication": {"mode": "PUBLIC_IMMEDIATE", "review_window_days": None,
                        "unresolved_disagreement": "PUBLISH_WITH_DISAGREEMENT"},
    }
    entry.update(overrides)
    return entry


def offers_doc(*entries):
    import json
    return json.dumps({"schema_version": "aacp-offers-v1", "offers": list(entries)}, indent=2) + "\n"


def producer_with_offer(test, name="toy-receipts", branch="main", **overrides):
    """A producer repository: commit 1 holds the subject files, commit 2 adds an offer
    over commit 1. Returns (offer ref, subject commit, repo path)."""
    import hashlib
    repo, subject_commit = test.remote_repo(name, fixture_files("toy-receipts"), branch)
    text = offers_doc(offer_entry(repo, subject_commit, **overrides))
    offer_commit = commit_files(test.remotes / name, {OFFER_PATH: text})
    ref = {"repo": repo, "commit": offer_commit, "path": OFFER_PATH, "offer_id": "toy-receipts-v1",
           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    return ref, subject_commit, test.remotes / name
