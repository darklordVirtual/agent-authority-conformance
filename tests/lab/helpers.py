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


def make_repo(root, files):
    """Create a git repository with files ({relpath: str|bytes}); return its commit."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    git("init", "--quiet", "-b", "main", cwd=root)
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

    def remote_repo(self, name, files):
        """Create a local repository reachable as https://example.invalid/<name>."""
        commit = make_repo(self.remotes / name, files)
        return REMOTE_PREFIX + name, commit

    def copy_fixture(self, name, dest):
        shutil.copytree(FIXTURES / name, dest, ignore=shutil.ignore_patterns("__pycache__"))
        return Path(dest)
