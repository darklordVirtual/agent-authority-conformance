"""Canonical JSON and hashing shared by every lab file."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .errors import ScopeError

FORBIDDEN_KEYS = frozenset({"overall", "score", "total", "aggregate", "grade"})


def dumps(obj) -> bytes:
    text = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def write_json(path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps(obj))


def _no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ScopeError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def read_json(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
        return json.loads(text, object_pairs_hook=_no_duplicates)
    except (OSError, json.JSONDecodeError) as exc:
        raise ScopeError(f"{path}: cannot read JSON: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def sha256_json(obj) -> str:
    return sha256_bytes(dumps(obj))


def find_forbidden_keys(obj, where="$"):
    """Paths of aggregate-like keys anywhere in obj. The lab never aggregates."""
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                found.append(f"{where}.{key}")
            found.extend(find_forbidden_keys(value, f"{where}.{key}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            found.extend(find_forbidden_keys(value, f"{where}[{i}]"))
    return found


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
