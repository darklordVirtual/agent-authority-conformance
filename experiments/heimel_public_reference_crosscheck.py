"""External diagnostic: AACP portable C/F/G semantics against HEIMEL v0.2.0 public reference adapter.

This is NOT an AACP self-service run and carries no BCR level. It executes
producer-published reference code under an external runner solely to discover
semantic mismatches and unsupported surfaces. Formal Federation publication
would require a separately frozen/admitted run under the AACP lab protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from aacp.adversarial import CASES, classify

HEIMEL_PROTOCOL = "HEIMEL-CONFORMANCE/2.0"
HEIMEL_RELEASE = "v0.2.0"
HEIMEL_COMMIT = "456e16935ac2cf0b4f47bc1343b5663cad240dea"


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _heimel_effect(call: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": call["tool"],
        "action": "invoke",
        "parameters": call.get("arguments", {}),
        "authority_version": "A2",
        "actor": "actor-1",
        "tenant": call.get("tenant", "tenant-a"),
    }


def _authority(effect: dict[str, Any], *, revoked: bool = False) -> dict[str, Any]:
    return {
        "present": True,
        "revoked": revoked,
        "valid_from": "2026-10-02T12:00:00Z",
        "expires_at": "2026-10-02T13:00:00Z",
        "checked_at": "2026-10-02T12:30:00Z",
        "scope": [f"{effect['id']}:{effect['action']}"],
        "version": "A2",
        "actor": "actor-1",
        "tenant": effect["tenant"],
        "delegation_chain_valid": True,
    }


def _invoke(adapter: Path, test: dict[str, Any]) -> dict[str, Any]:
    envelope = {"protocol": HEIMEL_PROTOCOL, "test": test}
    completed = subprocess.run(
        [sys.executable, str(adapter)],
        input=json.dumps(envelope),
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if completed.returncode != 0:
        return {
            "_adapter_error": f"exit={completed.returncode}",
            "_stderr": completed.stderr[-2000:],
        }
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {"_adapter_error": f"invalid JSON: {exc}", "_stdout": completed.stdout[-2000:]}
    return result


def _exact_call_observation(case: dict[str, Any], adapter: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    challenge = case["challenge"]
    authorized = challenge["authorized_call"]
    actual = challenge.get("late_mutation") or challenge["presented_call"]

    authorized_effect = _heimel_effect(authorized)
    actual_effect = _heimel_effect(actual)

    # Critical adversarial condition: the digest was computed before a late mutation
    # and the stale digest value is carried forward. A consequence-time boundary
    # must bind to/recompute from the concrete effect rather than trust this alias.
    stale_digest = _canonical_digest(authorized_effect)

    test = {
        "id": f"AACP-{case['id']}-HEIMEL",
        "group": "aacp_external_exact_call",
        "name": case["title"],
        "required": True,
        "mode": "single",
        "input": {
            "authority": _authority(authorized_effect),
            "effect": actual_effect,
            "required_info_complete": True,
            "authorized_effect_digest": stale_digest,
            "actual_effect_digest": stale_digest,
        },
    }
    raw = _invoke(adapter, test)
    if "_adapter_error" in raw:
        return {"execution": "ERROR", "message": raw["_adapter_error"]}, raw

    if raw.get("decision") == "ALLOW" or raw.get("effect_executed") is True:
        observation = {
            "execution": "COMPLETED",
            "outcome": "EXECUTED",
            "executed_call": actual,
        }
    else:
        observation = {"execution": "COMPLETED", "outcome": "REFUSED"}
    return observation, raw


def _freshness_observation(case: dict[str, Any], adapter: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if case["id"] != "F-01":
        message = "HEIMEL public reference protocol has no neutral mapping for this AACP freshness dimension"
        return {"execution": "UNSUPPORTED", "message": message}, {}

    call = {
        "tool": "update_record",
        "arguments": {"record": {"status": "approved"}},
        "tenant": "tenant-a",
        "target": "prod",
    }
    effect = _heimel_effect(call)
    test = {
        "id": "AACP-F-01-HEIMEL",
        "group": "aacp_external_freshness",
        "name": case["title"],
        "required": True,
        "mode": "single",
        "input": {
            "authority": _authority(effect, revoked=True),
            "effect": effect,
            "required_info_complete": True,
        },
    }
    raw = _invoke(adapter, test)
    if "_adapter_error" in raw:
        return {"execution": "ERROR", "message": raw["_adapter_error"]}, raw
    if raw.get("decision") == "ALLOW" or raw.get("effect_executed") is True:
        return {"execution": "COMPLETED", "outcome": "EXECUTED"}, raw
    return {"execution": "COMPLETED", "outcome": "REFUSED"}, raw


def _observation(case: dict[str, Any], adapter: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if case["property"] == "C":
        return _exact_call_observation(case, adapter)
    if case["property"] == "F":
        return _freshness_observation(case, adapter)
    return (
        {
            "execution": "UNSUPPORTED",
            "message": (
                "HEIMEL v0.2.0 public reference adapter does not expose the post-execution "
                "state-comparison / effect-receipt admission surface required by this AACP G case"
            ),
        },
        {},
    )


def run(heimel_root: Path) -> dict[str, Any]:
    adapter = heimel_root / "reference" / "adapter.py"
    if not adapter.is_file():
        raise FileNotFoundError(adapter)

    records = []
    for case in CASES:
        observation, heimel_raw = _observation(case, adapter)
        aacp = classify(case, observation)
        records.append(
            {
                "id": case["id"],
                "property": case["property"],
                "title": case["title"],
                "aacp": aacp,
                "observation": observation,
                "heimel_raw": heimel_raw,
            }
        )

    counts: dict[str, int] = {}
    for record in records:
        key = record["aacp"]["result"] or record["aacp"]["execution"]
        counts[key] = counts.get(key, 0) + 1

    return {
        "schema_version": "aacp-external-diagnostic-v1",
        "subject": {
            "repository": "Heimel-open/Heimel-",
            "release": HEIMEL_RELEASE,
            "commit": HEIMEL_COMMIT,
            "surface": "public reference adapter only",
        },
        "procedure": "AACP portable C/F/G classifier with runner-owned HEIMEL protocol bridge",
        "independence": "UNCLASSIFIED_EXTERNAL_DIAGNOSTIC",
        "bcr_level": None,
        "counts": counts,
        "records": records,
        "claim_ceiling": (
            "Diagnostic cross-check of HEIMEL's public reference adapter only. "
            "It does not establish or refute private VALO/REHT runtime properties, HEIMEL production "
            "deployment security, complete AACP C/F/G coverage, certification, or Federation admission."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--heimel-root", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-contradiction", action="store_true")
    args = parser.parse_args()

    document = run(args.heimel_root)
    payload = json.dumps(document, indent=2, sort_keys=True)
    print(payload)
    if args.json_out:
        args.json_out.write_text(payload + "\n", encoding="utf-8")

    if args.fail_on_contradiction and document["counts"].get("CONTRADICTED", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
