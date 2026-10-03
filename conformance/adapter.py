"""Read-only resolver for federation adapter manifests.

Resolution, evidence admission, property inference, review and publication are
separate claim boundaries. This module implements resolution only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

FORBIDDEN_CLAIM_KEYS = {"result", "status", "verdict", "score", "rating", "pass", "fail"}
ALLOWED_SOURCE_CLASSES = {
    "producer_artifact", "independent_observation", "test_fixture",
    "source_code", "run_record", "review_record",
}
REVIEW_MODES = {
    "PRIVATE_UNTIL_APPROVED",
    "PUBLIC_AFTER_REVIEW",
    "PUBLIC_IMMEDIATE",
    "PUBLIC_BY_MUTUAL_CONSENT",
}
DISAGREEMENT_POLICIES = {
    "PUBLISH_WITH_DISAGREEMENT", "HOLD_PUBLICATION", "SUPERSEDE_WITH_NEW_RUN",
}

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

def _review_policy(review: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy PR-5 review config to the explicit policy model."""
    if "mode" not in review:
        if review.get("maintainer_review_required") is not True:
            raise AdapterError("legacy review requires maintainer_review_required=true")
        return {
            "mode": "PRIVATE_UNTIL_APPROVED",
            "producer_review": "REQUIRED",
            "review_window_days": None,
            "unresolved_disagreement": "HOLD_PUBLICATION",
        }
    if review["mode"] not in REVIEW_MODES:
        raise AdapterError("unsupported review mode")
    producer_review = review.get("producer_review", "REQUIRED")
    if producer_review not in {"REQUIRED", "OPTIONAL", "NOT_REQUIRED"}:
        raise AdapterError("unsupported producer_review value")
    disagreement = review.get("unresolved_disagreement", "PUBLISH_WITH_DISAGREEMENT")
    if disagreement not in DISAGREEMENT_POLICIES:
        raise AdapterError("unsupported unresolved_disagreement value")
    days = review.get("review_window_days")
    if days is not None and (not isinstance(days, int) or isinstance(days, bool) or days < 0):
        raise AdapterError("review_window_days must be a non-negative integer or null")
    if review["mode"] == "PUBLIC_AFTER_REVIEW" and days is None:
        raise AdapterError("PUBLIC_AFTER_REVIEW requires review_window_days")
    return {
        "mode": review["mode"],
        "producer_review": producer_review,
        "review_window_days": days,
        "unresolved_disagreement": disagreement,
    }

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
    ids = [a.get("id") for a in m["artifacts"]]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise AdapterError("artifact ids must be nonempty and unique")
    for a in m["artifacts"]:
        if a.get("source_class") not in ALLOWED_SOURCE_CLASSES:
            raise AdapterError(f"unsupported source_class: {a.get('source_class')}")
        digest = a.get("sha256", "")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
            raise AdapterError("artifact sha256 must be 64 hex characters")
        p = Path(a.get("path", ""))
        if not a.get("path") or p.is_absolute() or ".." in p.parts:
            raise AdapterError("artifact paths must be relative and cannot traverse")
    for claim in m.get("claims", []):
        bad = FORBIDDEN_CLAIM_KEYS.intersection(k.lower() for k in claim)
        if bad:
            raise AdapterError(f"adapter claims cannot contain verdict fields: {sorted(bad)}")
        if not claim.get("claim_id") or not claim.get("claim_ceiling"):
            raise AdapterError("claims require claim_id and claim_ceiling")
        refs = set(claim.get("artifacts", []))
        known = {a["id"] for a in m["artifacts"]}
        if not refs or not refs.issubset(known):
            raise AdapterError("claim artifact references must resolve to declared artifacts")
        mapping = claim.get("aac_mapping")
        if mapping is not None and mapping.get("relationship") not in {
            "exact", "structural", "partial", "false_analog", "no_mapping", "not_evaluated"
        }:
            raise AdapterError("unsupported AAC mapping relationship")
    _review_policy(m.get("review", {}))

def _publication_state(policy: dict[str, Any]) -> tuple[str, bool]:
    mode = policy["mode"]
    if mode == "PUBLIC_IMMEDIATE":
        return "PUBLICATION_ALLOWED", True
    if mode == "PUBLIC_AFTER_REVIEW":
        return "PENDING_REVIEW_WINDOW", False
    if mode == "PUBLIC_BY_MUTUAL_CONSENT":
        return "PENDING_MUTUAL_CONSENT", False
    return "DRAFT_PRIVATE_REVIEW", False

def resolve(manifest: dict[str, Any], subject_root: str | Path) -> dict[str, Any]:
    validate_manifest(manifest)
    root = Path(subject_root).resolve()
    evidence = []
    states = {}
    for a in manifest["artifacts"]:
        p = (root / a["path"]).resolve()
        if root not in p.parents and p != root:
            raise AdapterError("resolved artifact escaped subject root")
        if not p.is_file():
            state, actual = "MISSING", None
        else:
            actual = sha256_bytes(p.read_bytes())
            state = "RESOLVED" if actual == a["sha256"].lower() else "HASH_MISMATCH"
        states[a["id"]] = state
        evidence.append({
            "artifact_id": a["id"], "path": a["path"], "source_class": a["source_class"],
            "expected_sha256": a["sha256"].lower(), "actual_sha256": actual, "resolution": state,
        })
    claims = []
    for c in manifest.get("claims", []):
        refs = c["artifacts"]
        ready = all(states[x] == "RESOLVED" for x in refs)
        claims.append({
            "claim_id": c["claim_id"],
            "native_claim": c.get("native_claim"),
            "aac_mapping": c.get("aac_mapping"),
            "procedure": c.get("procedure"),
            "artifacts": refs,
            "evidence_resolution": "RESOLVED" if ready else "INCOMPLETE",
            "claim_ceiling": c["claim_ceiling"],
            "property_verdict": None,
            "note": "Evidence resolution is not evidence admission and grants no A-G credit.",
        })
    required = [a["id"] for a in manifest["artifacts"] if a.get("required", True)]
    adapter_status = "RESOLVED" if all(states[x] == "RESOLVED" for x in required) else "INVALID_INPUT"
    policy = _review_policy(manifest.get("review", {}))
    review_state, publication_authorized = _publication_state(policy)
    return {
        "schema_version": "federation-evidence-bundle-v1",
        "subject": manifest["subject"],
        "adapter": manifest.get("adapter", {}),
        "adapter_status": adapter_status,
        "evidence": evidence,
        "claims": claims,
        "explicit_non_claims": manifest.get("explicit_non_claims", []),
        "review_policy": policy,
        "review_state": review_state,
        "publication_authorized": publication_authorized,
        "manifest_sha256": sha256_bytes(canonical_json(manifest)),
        "claim_ceiling": "This bundle establishes artifact resolution only. It is not an AAC property verdict, certification, endorsement, independent validation, or production claim.",
    }

def write_bundle(manifest_path: str | Path, subject_root: str | Path, out: str | Path) -> None:
    Path(out).write_bytes(canonical_json(resolve(load_manifest(manifest_path), subject_root)))
