"""Read-only resolver for federation adapter manifests.

This module resolves pinned evidence. It deliberately does not turn resolved
artifacts into A-G verdicts. Evidence admission and property inference remain
separate review steps.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

FORBIDDEN_CLAIM_KEYS = {"result", "status", "verdict", "score", "rating", "pass", "fail"}
ALLOWED_SOURCE_CLASSES = {"producer_artifact", "independent_observation", "test_fixture", "source_code", "run_record", "review_record"}

class AdapterError(ValueError):
    pass

def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_manifest(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest(data)
    return data

def validate_manifest(m: dict[str, Any]) -> None:
    if m.get("schema_version") != "federation-adapter-v1":
        raise AdapterError("unsupported schema_version")
    subject = m.get("subject", {})
    if not subject.get("repository") or not subject.get("revision"):
        raise AdapterError("subject repository and immutable revision are required")
    if len(subject["revision"]) != 40 or any(c not in "0123456789abcdef" for c in subject["revision"].lower()):
        raise AdapterError("subject revision must be a full 40-character commit SHA")
    adapter = m.get("adapter", {})
    arev = adapter.get("revision", "")
    if not adapter.get("id") or len(arev) != 40 or any(ch not in "0123456789abcdef" for ch in arev.lower()):
        raise AdapterError("adapter id and full 40-character revision are required")
    if not m.get("artifacts"):
        raise AdapterError("at least one pinned artifact is required")
    ids=[a.get("id") for a in m["artifacts"]]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise AdapterError("artifact ids must be nonempty and unique")
    for a in m["artifacts"]:
        if a.get("source_class") not in ALLOWED_SOURCE_CLASSES:
            raise AdapterError(f"unsupported source_class: {a.get('source_class')}")
        digest=a.get("sha256","")
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest.lower()):
            raise AdapterError("artifact sha256 must be 64 hex characters")
        p=Path(a.get("path",""))
        if not a.get("path") or p.is_absolute() or ".." in p.parts:
            raise AdapterError("artifact paths must be relative and cannot traverse")
    for claim in m.get("claims", []):
        bad=FORBIDDEN_CLAIM_KEYS.intersection(k.lower() for k in claim)
        if bad:
            raise AdapterError(f"adapter claims cannot contain verdict fields: {sorted(bad)}")
        if not claim.get("claim_id") or not claim.get("claim_ceiling"):
            raise AdapterError("claims require claim_id and claim_ceiling")
        refs=set(claim.get("artifacts", []))
        known={a["id"] for a in m["artifacts"]}
        if not refs or not refs.issubset(known):
            raise AdapterError("claim artifact references must resolve to declared artifacts")
    if not m.get("review", {}).get("maintainer_review_required", False):
        raise AdapterError("maintainer_review_required must be true")

def resolve(manifest: dict[str, Any], subject_root: str | Path) -> dict[str, Any]:
    validate_manifest(manifest)
    root=Path(subject_root).resolve()
    evidence=[]
    states={}
    for a in manifest["artifacts"]:
        p=(root/a["path"]).resolve()
        if root not in p.parents and p != root:
            raise AdapterError("resolved artifact escaped subject root")
        if not p.is_file():
            state="MISSING"
            actual=None
        else:
            actual=sha256_bytes(p.read_bytes())
            state="RESOLVED" if actual == a["sha256"].lower() else "HASH_MISMATCH"
        states[a["id"]]=state
        evidence.append({
            "artifact_id":a["id"], "path":a["path"], "source_class":a["source_class"],
            "expected_sha256":a["sha256"].lower(), "actual_sha256":actual, "resolution":state
        })
    claims=[]
    for c in manifest.get("claims", []):
        refs=c["artifacts"]
        ready=all(states[x]=="RESOLVED" for x in refs)
        claims.append({
            "claim_id":c["claim_id"], "property":c.get("property"),
            "procedure":c.get("procedure"), "artifacts":refs,
            "evidence_resolution":"RESOLVED" if ready else "INCOMPLETE",
            "claim_ceiling":c["claim_ceiling"],
            "property_verdict":None,
            "note":"Evidence resolution is not evidence admission and grants no A-G credit."
        })
    required=[a["id"] for a in manifest["artifacts"] if a.get("required", True)]
    adapter_status="RESOLVED" if all(states[x]=="RESOLVED" for x in required) else "INVALID_INPUT"
    return {
        "schema_version":"federation-evidence-bundle-v1",
        "subject":manifest["subject"],
        "adapter":manifest.get("adapter", {}),
        "adapter_status":adapter_status,
        "evidence":evidence,
        "claims":claims,
        "explicit_non_claims":manifest.get("explicit_non_claims", []),
        "review_state":"DRAFT_PRIVATE_REVIEW",
        "publication_authorized":False,
        "manifest_sha256":sha256_bytes(canonical_json(manifest)),
        "claim_ceiling":"This bundle establishes artifact resolution only. It is not an AAC property verdict, certification, endorsement, independent validation, or production claim."
    }

def write_bundle(manifest_path: str | Path, subject_root: str | Path, out: str | Path) -> None:
    Path(out).write_bytes(canonical_json(resolve(load_manifest(manifest_path), subject_root)))
