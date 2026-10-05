"""Portable, vendor-neutral adversarial probes for AACP properties C, F and G.

This module is intentionally implementation-neutral.  An implementation supplies
one adapter function::

    def run_case(case: dict) -> dict: ...

The adapter receives a challenge without an expected answer.  AACP owns the
classification rule and produces ESTABLISHED / CONTRADICTED / NOT_ESTABLISHED,
or a non-verdict execution state.  A local run is SELF_RUN evidence only: it is
not independent verification, certification or a Federation admission record.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable

SUITE_VERSION = "aacp-portable-cfg-adversarial-v1"
PROPERTIES = ("C", "F", "G")
EXECUTIONS = ("COMPLETED", "UNSUPPORTED", "INVALID_INPUT", "ERROR")
RESULTS = ("ESTABLISHED", "CONTRADICTED", "NOT_ESTABLISHED")
SELF_RUN_CEILING = (
    "Local SELF_RUN of vendor-neutral C/F/G adversarial cases only. "
    "The result does not establish independent reproduction, production security, "
    "execution-boundary integrity, semantic authority, certification or Federation adoption."
)


def _case(case_id: str, property_id: str, kind: str, title: str,
          challenge: dict[str, Any], claim_ceiling: str) -> dict[str, Any]:
    return {
        "id": case_id,
        "property": property_id,
        "kind": kind,
        "title": title,
        "challenge": challenge,
        "claim_ceiling": claim_ceiling,
    }


CASES: tuple[dict[str, Any], ...] = (
    _case(
        "C-01", "C", "exact_call", "Nested argument mutation",
        {
            "authorized_call": {
                "tool": "update_record",
                "arguments": {"record": {"status": "approved", "meta": {"count": 1}}},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "presented_call": {
                "tool": "update_record",
                "arguments": {"record": {"status": "approved", "meta": {"count": 2}}},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "mutation_phase": "before_dispatch",
        },
        "Establishes only that a nested value change cannot execute under authority for the original call.",
    ),
    _case(
        "C-02", "C", "exact_call", "Nested key deletion",
        {
            "authorized_call": {
                "tool": "update_record",
                "arguments": {"record": {"status": "approved", "reason": "reviewed"}},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "presented_call": {
                "tool": "update_record",
                "arguments": {"record": {"status": "approved"}},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "mutation_phase": "before_dispatch",
        },
        "Establishes only that deleting a nested authorized argument cannot preserve exact-call authority.",
    ),
    _case(
        "C-03", "C", "exact_call", "Scalar-kind substitution",
        {
            "authorized_call": {
                "tool": "set_priority",
                "arguments": {"priority": 1},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "presented_call": {
                "tool": "set_priority",
                "arguments": {"priority": "1"},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "mutation_phase": "before_dispatch",
        },
        "Establishes only that a string/integer substitution is not treated as the same authorized call.",
    ),
    _case(
        "C-04", "C", "exact_call", "Verify-then-mutate",
        {
            "authorized_call": {
                "tool": "transfer",
                "arguments": {"amount": 1, "currency": "NOK"},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "presented_call": {
                "tool": "transfer",
                "arguments": {"amount": 1, "currency": "NOK"},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "late_mutation": {
                "tool": "transfer",
                "arguments": {"amount": 999, "currency": "NOK"},
                "tenant": "tenant-a",
                "target": "prod",
            },
            "mutation_phase": "after_binding_check_before_invoke",
        },
        "Establishes only that a call cannot change after its binding check and still execute under the earlier authority.",
    ),
    _case(
        "F-01", "F", "freshness", "Authority revoked after approval",
        {
            "authorized_context": {"authority_state": "active", "authority_epoch": 7},
            "dispatch_context": {"authority_state": "revoked", "authority_epoch": 8},
            "changed": ["authority_state", "authority_epoch"],
        },
        "Establishes only that a revocation visible before dispatch prevents use of the stale authorization.",
    ),
    _case(
        "F-02", "F", "freshness", "Tool definition changes before dispatch",
        {
            "authorized_context": {"tool_definition_digest": "sha256:spec-a"},
            "dispatch_context": {"tool_definition_digest": "sha256:spec-b"},
            "changed": ["tool_definition_digest"],
        },
        "Establishes only that a changed tool definition cannot silently inherit prior authority.",
    ),
    _case(
        "F-03", "F", "freshness", "Callable identity changes before dispatch",
        {
            "authorized_context": {"callable_identity": "worker-v1"},
            "dispatch_context": {"callable_identity": "worker-v2"},
            "changed": ["callable_identity"],
        },
        "Establishes only that the implementation invoked is coherent with the implementation checked for the authorization.",
    ),
    _case(
        "F-04", "F", "freshness", "Policy revision changes before dispatch",
        {
            "authorized_context": {"policy_revision": "policy-17"},
            "dispatch_context": {"policy_revision": "policy-18"},
            "changed": ["policy_revision"],
        },
        "Establishes only that a stale policy context is not silently accepted after a revision change.",
    ),
    _case(
        "F-05", "F", "freshness", "Fresh hard guard becomes active",
        {
            "authorized_context": {"hard_guard": False},
            "dispatch_context": {"hard_guard": True},
            "changed": ["hard_guard"],
        },
        "Establishes only that a load-bearing fresh guard observed before dispatch can prevent the effect.",
    ),
    _case(
        "F-06", "F", "freshness", "Capability epoch advances",
        {
            "authorized_context": {"capability_epoch": 3},
            "dispatch_context": {"capability_epoch": 4},
            "changed": ["capability_epoch"],
        },
        "Establishes only that capability authority cannot be used after the relevant revocation/freshness epoch advances.",
    ),
    _case(
        "G-01", "G", "effect_compare", "Absent field is not explicit null",
        {
            "contract": {
                "expected_fields": {"deleted_at": None},
                "comparison_rules": {"deleted_at": "exact"},
            },
            "observed": {},
        },
        "Establishes only that an absent property is distinguished from an explicitly present null for an exact postcondition.",
    ),
    _case(
        "G-02", "G", "effect_compare", "Unknown comparison rule",
        {
            "contract": {
                "expected_fields": {"status": "closed"},
                "comparison_rules": {"status": "excat"},
            },
            "observed": {"status": "closed"},
        },
        "Establishes only that an unknown postcondition rule is refused or treated as invalid, never silently interpreted as a passing known rule.",
    ),
    _case(
        "G-03", "G", "effect_compare", "Rule for undeclared field",
        {
            "contract": {
                "expected_fields": {"status": "closed"},
                "comparison_rules": {"undeclared": "exact"},
            },
            "observed": {"status": "closed"},
        },
        "Establishes only that structurally unused postcondition rules are rejected instead of silently ignored.",
    ),
    _case(
        "G-04", "G", "receipt", "Forged tool identity in effect receipt",
        {
            "lineage": {
                "proposal_id": "p-1",
                "tool_id": "update_record",
                "tool_definition_digest": "sha256:spec-a",
                "dispatch_id": "d-1",
            },
            "receipt": {
                "proposal_id": "p-1",
                "tool_id": "delete_record",
                "tool_definition_digest": "sha256:spec-a",
                "dispatch_id": "d-1",
                "status": "EFFECT_VERIFIED",
                "reason_code": "postcondition_verified",
            },
        },
        "Establishes only that effect evidence naming a different tool cannot be admitted as evidence for the dispatch.",
    ),
    _case(
        "G-05", "G", "receipt", "Forged tool-definition identity in effect receipt",
        {
            "lineage": {
                "proposal_id": "p-1",
                "tool_id": "update_record",
                "tool_definition_digest": "sha256:spec-a",
                "dispatch_id": "d-1",
            },
            "receipt": {
                "proposal_id": "p-1",
                "tool_id": "update_record",
                "tool_definition_digest": "sha256:spec-b",
                "dispatch_id": "d-1",
                "status": "EFFECT_VERIFIED",
                "reason_code": "postcondition_verified",
            },
        },
        "Establishes only that effect evidence is bound to the tool definition associated with the dispatch.",
    ),
    _case(
        "G-06", "G", "receipt", "Contradictory terminal status and reason",
        {
            "lineage": {
                "proposal_id": "p-1",
                "tool_id": "update_record",
                "tool_definition_digest": "sha256:spec-a",
                "dispatch_id": "d-1",
            },
            "receipt": {
                "proposal_id": "p-1",
                "tool_id": "update_record",
                "tool_definition_digest": "sha256:spec-a",
                "dispatch_id": "d-1",
                "status": "EFFECT_VERIFIED",
                "reason_code": "postcondition_field_mismatch",
            },
        },
        "Establishes only that internally contradictory terminal effect evidence is not admitted unchanged.",
    ),
    _case(
        "G-07", "G", "receipt_sequence", "Unbound unresolved report cannot poison later verification",
        {
            "lineage": {
                "proposal_id": "p-1",
                "tool_id": "update_record",
                "tool_definition_digest": "sha256:spec-a",
                "dispatch_id": "d-1",
            },
            "submissions": [
                {
                    "id": "unbound_unsupported",
                    "receipt": {
                        "proposal_id": "p-1",
                        "status": "EFFECT_UNSUPPORTED",
                        "tool_id": "",
                        "tool_definition_digest": "",
                        "dispatch_id": "",
                    },
                },
                {
                    "id": "legitimate_verified",
                    "receipt": {
                        "proposal_id": "p-1",
                        "status": "EFFECT_VERIFIED",
                        "tool_id": "update_record",
                        "tool_definition_digest": "sha256:spec-a",
                        "dispatch_id": "d-1",
                        "reason_code": "postcondition_verified",
                    },
                },
            ],
        },
        "Establishes only that an unresolved/unbound report cannot consume the terminal slot needed by later bound effect evidence.",
    ),
)


class AdapterError(ValueError):
    pass


def _json_same(left: Any, right: Any) -> bool:
    """Deep equality with scalar kind significance and no bool/int collapse."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_json_same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_json_same(a, b) for a, b in zip(left, right))
    return left == right


def _nonverdict(case: dict[str, Any], execution: str, message: str = "") -> dict[str, Any]:
    return {
        "id": case["id"],
        "property": case["property"],
        "execution": execution,
        "result": None,
        "detail": message,
        "claim_ceiling": case["claim_ceiling"],
    }


def _classified(case: dict[str, Any], result: str, detail: str) -> dict[str, Any]:
    return {
        "id": case["id"],
        "property": case["property"],
        "execution": "COMPLETED",
        "result": result,
        "detail": detail,
        "claim_ceiling": case["claim_ceiling"],
    }


def classify(case: dict[str, Any], observation: Any) -> dict[str, Any]:
    """Classify one adapter observation. Expected answers never enter the adapter."""
    if not isinstance(observation, dict):
        return _nonverdict(case, "ERROR", "adapter must return a mapping")
    execution = observation.get("execution", "COMPLETED")
    if execution not in EXECUTIONS:
        return _nonverdict(case, "ERROR", f"unknown execution state {execution!r}")
    if execution != "COMPLETED":
        return _nonverdict(case, execution, str(observation.get("message", "")))

    kind = case["kind"]
    if kind == "exact_call":
        outcome = observation.get("outcome")
        if outcome == "REFUSED":
            return _classified(case, "ESTABLISHED", "mutated/non-identical call was refused")
        if outcome != "EXECUTED":
            return _classified(case, "NOT_ESTABLISHED", "adapter did not report REFUSED or EXECUTED")
        executed = observation.get("executed_call")
        if _json_same(executed, case["challenge"]["authorized_call"]):
            return _classified(case, "ESTABLISHED", "only the exactly authorized call executed")
        return _classified(case, "CONTRADICTED", "a call different from the authorized call executed")

    if kind == "freshness":
        outcome = observation.get("outcome")
        if outcome == "REFUSED":
            return _classified(case, "ESTABLISHED", "changed authorization context prevented dispatch")
        if outcome == "EXECUTED":
            return _classified(case, "CONTRADICTED", "execution proceeded after a load-bearing context change")
        return _classified(case, "NOT_ESTABLISHED", "adapter did not report REFUSED or EXECUTED")

    if kind == "effect_compare":
        status = observation.get("effect_status")
        outcome = observation.get("outcome")
        if case["id"] == "G-01":
            if status == "EFFECT_MISMATCH":
                return _classified(case, "ESTABLISHED", "absence was distinguished from explicit null")
            if status == "EFFECT_VERIFIED":
                return _classified(case, "CONTRADICTED", "missing field was falsely treated as exact null")
            return _classified(case, "NOT_ESTABLISHED", "no decisive effect comparison result")
        if outcome in {"REFUSED", "INVALID_INPUT"} or observation.get("execution") == "INVALID_INPUT":
            return _classified(case, "ESTABLISHED", "invalid postcondition contract was rejected")
        if status == "EFFECT_VERIFIED":
            return _classified(case, "CONTRADICTED", "invalid postcondition structure produced a verified effect")
        return _classified(case, "NOT_ESTABLISHED", "invalid rule was neither clearly rejected nor falsely verified")

    if kind == "receipt":
        outcome = observation.get("outcome")
        if outcome == "REFUSED":
            return _classified(case, "ESTABLISHED", "contradictory or forged receipt was refused")
        if outcome == "ACCEPTED":
            return _classified(case, "CONTRADICTED", "contradictory or forged receipt was admitted")
        return _classified(case, "NOT_ESTABLISHED", "adapter did not report receipt admission/refusal")

    if kind == "receipt_sequence":
        steps = observation.get("steps")
        if not isinstance(steps, list):
            return _classified(case, "NOT_ESTABLISHED", "adapter did not report both receipt submissions")
        by_id = {step.get("id"): step for step in steps if isinstance(step, dict)}
        first = by_id.get("unbound_unsupported", {}).get("outcome")
        second = by_id.get("legitimate_verified", {}).get("outcome")
        if second == "ACCEPTED":
            return _classified(case, "ESTABLISHED", "later bound verification retained a usable settlement path")
        if first == "ACCEPTED" and second == "REFUSED":
            return _classified(case, "CONTRADICTED", "unbound unresolved report poisoned the terminal settlement slot")
        return _classified(case, "NOT_ESTABLISHED", "receipt sequence did not establish whether terminal-slot poisoning is possible")

    return _nonverdict(case, "ERROR", f"runner does not know case kind {kind!r}")


def load_adapter(spec: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    module_name, sep, function_name = spec.rpartition(":")
    if not sep or not module_name or not function_name:
        raise AdapterError("--adapter must be <module-or-path>:<function>")
    path = Path(module_name)
    if path.is_file() or module_name.endswith(".py"):
        if not path.is_file():
            raise AdapterError(f"adapter file does not exist: {path}")
        module_spec = importlib.util.spec_from_file_location("aacp_portable_adapter", path)
        if module_spec is None or module_spec.loader is None:
            raise AdapterError(f"cannot load adapter file: {path}")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
    else:
        module = importlib.import_module(module_name)
    function = getattr(module, function_name, None)
    if not callable(function):
        raise AdapterError(f"{function_name!r} is not callable in {module_name!r}")
    return function


def run(adapter: Callable[[dict[str, Any]], dict[str, Any]],
        properties: tuple[str, ...] = PROPERTIES) -> dict[str, Any]:
    records = []
    for case in CASES:
        if case["property"] not in properties:
            continue
        challenge = copy.deepcopy(case)
        try:
            observation = adapter(challenge)
        except Exception as exc:  # producer/subject adapter failure is a non-verdict
            records.append(_nonverdict(case, "ERROR", f"{type(exc).__name__}: {exc}"))
            continue
        records.append(classify(case, observation))
    return {
        "schema_version": "aacp-adversarial-run-v1",
        "suite_version": SUITE_VERSION,
        "independence": "SELF_RUN",
        "bcr_level": "BCR-0",
        "properties": list(properties),
        "cases": records,
        "claim_ceiling": SELF_RUN_CEILING,
    }


def _print_text(document: dict[str, Any]) -> None:
    print(f"{document['suite_version']} ({document['independence']}, {document['bcr_level']})")
    current = None
    for row in document["cases"]:
        if row["property"] != current:
            current = row["property"]
            print(f"\nProperty {current}")
        result = row["result"] or row["execution"]
        print(f"  {row['id']}: {result} — {row['detail']}")
    print(f"\nClaim ceiling: {document['claim_ceiling']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aacp adversarial",
        description="Run vendor-neutral C/F/G adversarial probes against a local implementation adapter.",
    )
    parser.add_argument("--adapter", help="<module-or-path>:<function>")
    parser.add_argument("--property", action="append", choices=PROPERTIES, dest="properties")
    parser.add_argument("--list", action="store_true", help="list built-in cases without executing an adapter")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-supported",
        action="store_true",
        help="exit nonzero when any selected case is UNSUPPORTED/INVALID_INPUT/ERROR/NOT_ESTABLISHED",
    )
    args = parser.parse_args(argv)

    selected = tuple(dict.fromkeys(args.properties or PROPERTIES))
    if args.list:
        rows = [copy.deepcopy(case) for case in CASES if case["property"] in selected]
        if args.json:
            print(json.dumps({"suite_version": SUITE_VERSION, "cases": rows}, sort_keys=True))
        else:
            for row in rows:
                print(f"{row['id']} [{row['property']}] {row['title']}")
        return 0
    if not args.adapter:
        parser.error("--adapter is required unless --list is used")

    try:
        adapter = load_adapter(args.adapter)
        document = run(adapter, selected)
    except (AdapterError, ImportError, OSError) as exc:
        print(f"aacp adversarial: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(document, sort_keys=True, ensure_ascii=True))
    else:
        _print_text(document)

    contradicted = any(row["result"] == "CONTRADICTED" for row in document["cases"])
    incomplete = any(
        row["execution"] != "COMPLETED" or row["result"] == "NOT_ESTABLISHED"
        for row in document["cases"]
    )
    if contradicted:
        return 1
    if args.require_supported and incomplete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
