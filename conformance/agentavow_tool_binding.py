"""Independent Python consumer for AgentAvow MCP tool-definition binding vectors.

This module intentionally imports no AgentAvow implementation code.  It implements
only the published v1 derivation needed to reproduce the federation edge.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PROFILE = "agentavow.mcp-tool-definition.v1"
TOOL_FIELDS = ("name", "title", "description", "inputSchema", "outputSchema", "annotations")


def _b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonicalize(value: Any) -> bytes:
    # The pinned corpus contains only JSON primitives whose Python serialization is
    # identical to RFC 8785 JCS.  This is deliberately narrow, not a general JCS API.
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def tool_key(name: str) -> str:
    encoded = []
    for ch in name:
        code = ord(ch)
        if 0x21 <= code <= 0x7E and ch not in "%=":
            encoded.append(ch)
        else:
            encoded.extend(f"%{byte:02X}" for byte in ch.encode("utf-8"))
    body = "".join(encoded)
    if len(body) > 128:
        suffix = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
        body = body[:96] + "~" + suffix
    return "tool:" + body


def tool_digest(tool: dict[str, Any]) -> str:
    selected = {k: tool[k] for k in TOOL_FIELDS if k in tool and tool[k] is not None}
    preimage = {"profile": PROFILE, "tool": selected}
    return "sha256:" + hashlib.sha256(canonicalize(preimage)).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate(vector: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    compact = fixture["attestation"]["jws"] if vector["jws"] == "reference" else vector["jws"]
    header64, payload64, sig64 = compact.split(".")
    header = json.loads(_b64url(header64))
    payload_bytes = _b64url(payload64)
    payload = json.loads(payload_bytes)

    jwk = fixture["issuer"]["jwk"]
    signature_valid = False
    if header.get("alg") == "EdDSA" and header.get("kid") == jwk.get("kid"):
        try:
            Ed25519PublicKey.from_public_bytes(_b64url(jwk["x"])).verify(
                _b64url(sig64), f"{header64}.{payload64}".encode("ascii")
            )
            signature_valid = True
        except Exception:
            signature_valid = False

    canonical_bytes = canonicalize(payload) == payload_bytes
    gate = vector["gate"]
    subject_binds = payload.get("subject", {}).get("id") == gate["subject_id"]
    key = tool_key(gate["tool_name"])
    signed_digest = payload.get("scan", {}).get("toolDigests", {}).get(key)
    tool_binds = signed_digest is not None
    tool_digest_binds: bool | str = (
        signed_digest == gate["observed_tool_digest"] if tool_binds else "not_evaluated"
    )
    when = _parse_time(gate["evaluation_time"])
    fresh = _parse_time(payload["issuedAt"]) <= when < _parse_time(payload["expiresAt"])
    rely = all(
        x is True
        for x in (
            signature_valid,
            canonical_bytes,
            subject_binds,
            tool_binds,
            tool_digest_binds,
            fresh,
        )
    )
    return {
        "signature_valid": signature_valid,
        "canonical_bytes": canonical_bytes,
        "subject_binds": subject_binds,
        "tool_binds": tool_binds,
        "tool_digest_binds": tool_digest_binds,
        "fresh": fresh,
        "rely": rely,
    }
