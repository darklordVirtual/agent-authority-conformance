"""gh and git calls for share and publish (RUN-PROTOCOL-v0.3 §4).

Every failure raises GitHubError before lifecycle state changes, so commands are
safe to retry. AAC_GH overrides the gh command and AAC_GIT_REMOTE_BASE the push
base URL (both used by tests).
"""

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .errors import GitHubError

SKIP_PARTS = frozenset({".git", ".local", "__pycache__", "reruns"})


def _gh_command():
    return shlex.split(os.environ.get("AAC_GH", "gh"))


def gh(*args):
    result = subprocess.run([*_gh_command(), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise GitHubError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git(*args, cwd):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitHubError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def remote_url(full_name):
    return f"{os.environ.get('AAC_GIT_REMOTE_BASE', 'https://github.com')}/{full_name}.git"


def owner_type(owner):
    return gh("api", f"users/{owner}", "--jq", ".type")


def visibility(full_name):
    return gh("repo", "view", full_name, "--json", "visibility", "--jq", ".visibility")


def exists(full_name):
    try:
        visibility(full_name)
        return True
    except GitHubError:
        return False


def create_private(full_name):
    if not exists(full_name):
        gh("repo", "create", full_name, "--private",
           "--description", "Agent Authority Conformance run package (private first)")
    if visibility(full_name) != "PRIVATE":
        raise GitHubError(f"{full_name} is not private; refusing to push")


def invite_read_only(full_name, user):
    gh("api", "-X", "PUT", f"repos/{full_name}/collaborators/{user}", "-f", "permission=pull")


def make_public(full_name):
    gh("repo", "edit", full_name, "--visibility", "public", "--accept-visibility-change-consequences")
    if visibility(full_name) != "PUBLIC":
        raise GitHubError(f"{full_name} did not become public")


def push_snapshot(run_dir, full_name, message, files=None):
    """Copy the package (or the named files) into a clone of the remote, commit, push.
    Returns the pushed commit."""
    src = Path(run_dir)
    names = files if files is not None else [
        p.relative_to(src).as_posix() for p in sorted(src.rglob("*"))
        if p.is_file() and not (set(p.relative_to(src).parts) & SKIP_PARTS)]
    with tempfile.TemporaryDirectory(prefix="aac-share-") as tmp:
        work = Path(tmp) / "repo"
        git("clone", "--quiet", remote_url(full_name), str(work), cwd=tmp)
        if files is None:
            # A full delivery replaces the tree, so stale remote files cannot survive.
            git("rm", "-r", "-q", "--ignore-unmatch", ".", cwd=work)
        for rel in names:
            dest = work / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, dest)
        git("add", "-A", cwd=work)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work).returncode == 0:
            return git("rev-parse", "HEAD", cwd=work)  # already delivered: retries are no-ops
        git("commit", "--quiet", "-m", message, cwd=work)
        git("push", "--quiet", "origin", "HEAD:main", cwd=work)
        return git("rev-parse", "HEAD", cwd=work)
