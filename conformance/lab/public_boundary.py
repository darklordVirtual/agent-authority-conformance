"""Pinned public-boundary basis for self-service verification.

This is deliberately smaller than a producer offer.  It records only the public
artifact that the runner relied on.  It is not producer consent, endorsement,
admission, or an AACP-native statement.

A runner may use this basis when a producer has already published a frozen
artifact/boundary/procedure for public reproduction.  AACP then publishes only
its own attributed run record.  Claims and classification must stay within the
pinned public boundary; checking that semantic mapping remains the runner's
review responsibility, not something inferred from publication alone.
"""

import re
import tempfile
from pathlib import Path, PurePosixPath

from .canonical import sha256_file
from .errors import PinError, ScopeError
from .pins import fetch

COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _relative(path):
    pure = PurePosixPath(path)
    return _text(path) and not pure.is_absolute() and ".." not in pure.parts


def validate_ref(ref):
    if not (isinstance(ref, dict)
            and _text(ref.get("repo")) and ref["repo"].startswith("https://")
            and isinstance(ref.get("commit"), str) and COMMIT.fullmatch(ref["commit"])
            and _relative(ref.get("path"))
            and isinstance(ref.get("sha256"), str) and SHA256.fullmatch(ref["sha256"])
            and _text(ref.get("procedure_ref"))
            and _text(ref.get("claims_ref"))
            and _text(ref.get("classification_ref"))):
        raise ScopeError(
            "public_boundary must contain repo (https), commit (40 hex), path (relative), "
            "sha256, procedure_ref, claims_ref and classification_ref"
        )
    return ref


def verify_pinned(ref, workdir=None):
    """Verify the exact public boundary bytes.  Never execute producer code."""
    validate_ref(ref)
    with tempfile.TemporaryDirectory(prefix="aac-public-boundary-", dir=workdir) as tmp:
        clone = fetch(ref["repo"], ref["commit"], Path(tmp) / "boundary")
        path = clone / ref["path"]
        if not path.is_file():
            raise PinError(f"{ref['path']} does not exist at public boundary commit {ref['commit']}")
        if sha256_file(path) != ref["sha256"]:
            raise PinError(f"{ref['path']} at {ref['commit']} does not have the pinned sha256")
    return ref


def source_url(ref):
    validate_ref(ref)
    return f"{ref['repo'].rstrip('/')}/blob/{ref['commit']}/{ref['path']}"
