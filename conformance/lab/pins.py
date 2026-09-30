"""Fetch pinned subjects and verify per-file SHA-256 (RUN-PROTOCOL-v0.3 P1).

Fetching is the only network step of a run or rerun, and it happens before any
subject code executes.
"""

import shutil
import subprocess
from pathlib import Path

from .canonical import sha256_file
from .errors import PinError

LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")


def _git(*args, cwd=None):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PinError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def fetch(repo, commit, dest):
    """Clone repo into dest and check out exactly commit."""
    dest = Path(dest)
    _git("clone", "--quiet", "--no-checkout", repo, str(dest))
    _git("-c", "advice.detachedHead=false", "checkout", "--quiet", commit, cwd=dest)
    head = _git("rev-parse", "HEAD", cwd=dest)
    if head != commit:
        raise PinError(f"{repo}: HEAD {head} is not the pinned commit {commit}")
    return dest


def hash_paths(root, paths):
    """SHA-256 of every file under the declared paths, keyed by posix path."""
    root, out = Path(root), {}
    for rel in paths:
        target = root / rel
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = sorted(p for p in target.rglob("*")
                           if p.is_file() and ".git" not in p.relative_to(root).parts)
        else:
            raise PinError(f"declared path {rel} does not exist at the pinned commit")
        for path in files:
            out[path.relative_to(root).as_posix()] = sha256_file(path)
    return dict(sorted(out.items()))


def verify(root, expected):
    root = Path(root)
    bad = sorted(rel for rel, digest in expected.items()
                 if not (root / rel).is_file() or sha256_file(root / rel) != digest)
    if bad:
        raise PinError("pinned bytes differ or are missing: " + ", ".join(bad))


def export(clone, paths, dest):
    """Copy only the declared paths; engines never see the rest of the repository."""
    clone, dest = Path(clone), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for rel in paths:
        src, dst = clone / rel, dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git"), dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    return dest


def materialize(scope, workdir):
    """Fetch, verify and export every subject: (trees, licence texts) by subject index."""
    workdir, trees, licenses = Path(workdir), {}, {}
    for i, subject in enumerate(scope["subjects"]):
        clone = fetch(subject["repo"], subject["commit"], workdir / f"clone-{i}")
        verify(clone, subject["files_sha256"])
        extra = sorted(set(hash_paths(clone, subject["paths"])) - set(subject["files_sha256"]))
        if extra:
            raise PinError(f"subject {i}: unpinned files under declared paths: {', '.join(extra)}")
        trees[i] = export(clone, subject["paths"], workdir / f"tree-{i}")
        found = next((clone / n for n in LICENSE_NAMES if (clone / n).is_file()), None)
        licenses[i] = found.read_text(encoding="utf-8", errors="replace") if found else None
    return trees, licenses
