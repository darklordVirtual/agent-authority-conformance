#!/usr/bin/env python3
"""A second implementation of six AACP reference-vector operations, standard library only.

    python -m conformance.vectors run --impl "python templates/vector-impl/stdlib_impl.py"

It reads one request on stdin and writes one response on stdout
(docs/REFERENCE-VECTORS.md). It imports nothing from this repository and was
written from the operation contracts in the vector files and the specification
texts they cite, not from conformance/*.py. It is a template: copy it into
another language, or replace it.

It is NOT an independent implementation in the AACP sense: the same project
wrote it, so agreement shows that the contracts are implementable as written,
not that a separate party reached the same answers. Operations it does not
implement (the E rule, the coverage matrix and the AgentAvow signature check,
which need the JSON schemas or Ed25519) answer UNSUPPORTED_OPERATION.
"""
from __future__ import annotations

import hashlib
import json
import sys

FORBIDDEN = ("overall", "score", "total", "aggregate", "grade")


def canonical_json(value):
    text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    return {"result": {"canonical_utf8": text,
                       "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}}


def read_json(text):
    def strict(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise KeyError("duplicate")
        return dict(pairs)
    try:
        return {"result": json.loads(text, object_pairs_hook=strict)}
    except KeyError:
        return {"error": "DUPLICATE_KEY"}
    except json.JSONDecodeError:
        return {"error": "INVALID_JSON"}


def forbidden_keys(value, where="$"):
    found = []
    if isinstance(value, dict):
        for key, inner in value.items():
            if key in FORBIDDEN:
                found.append(f"{where}.{key}")
            found.extend(forbidden_keys(inner, f"{where}.{key}"))
    elif isinstance(value, list):
        for i, inner in enumerate(value):
            found.extend(forbidden_keys(inner, f"{where}[{i}]"))
    return found


def tool_key(name):
    body = ""
    for ch in name:
        if 0x21 <= ord(ch) <= 0x7E and ch not in "%=":
            body += ch
        else:
            body += "".join(f"%{b:02X}" for b in ch.encode("utf-8"))
    if len(body) > 128:
        body = body[:96] + "~" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
    return "tool:" + body


def tool_digest(tool):
    fields = ("name", "title", "description", "inputSchema", "outputSchema", "annotations")
    selected = {k: tool[k] for k in fields if tool.get(k) is not None}
    preimage = {"profile": "agentavow.mcp-tool-definition.v1", "tool": selected}
    jcs = json.dumps(preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(jcs.encode("utf-8")).hexdigest()


def vantage(record, trusted):
    def text(name):
        v = record.get(name)
        return v if isinstance(v, str) and v.strip() else None

    def verdict(result, unmet, reason):
        return {"result": {"result": result, "unmet_obligation": unmet, "reason": reason}}

    def not_established(reason):
        return verdict("NOT_ESTABLISHED", "observation_vantage", reason)

    if not isinstance(record, dict):
        return verdict("INVALID_INPUT", None, "record-not-an-object")
    observer, observed = text("observer_id"), text("observed_party")
    if observer is None or observed is None:
        return verdict("INVALID_INPUT", None, "observer-identity-invalid")
    if not isinstance(record.get("declared_independence", False), bool):
        return verdict("INVALID_INPUT", None, "declared-independence-not-boolean")
    if observer == observed:                                            # profile rule 1
        return not_established("authoritative-vantage-not-independent")
    forge, suppress = record.get("can_observed_party_forge"), record.get("can_observed_party_suppress")
    for v in (forge, suppress):
        if v is not None and not isinstance(v, bool):
            return verdict("INVALID_INPUT", None, "capability-not-boolean")
    if forge is True or suppress is True:                               # rule 2
        return not_established("authoritative-vantage-not-independent")
    mine, theirs = text("control_domain"), text("observed_control_domain")
    if mine is None or theirs is None:                                  # rule 5
        return not_established("observation-vantage-not-established")
    if mine == theirs:                                                  # rule 3
        return not_established("authoritative-vantage-not-independent")
    if mine not in set(trusted) or forge is not False or suppress is not False:   # rules 4, 5
        return not_established("observation-vantage-not-established")
    return verdict("ESTABLISHED", None, "independent-vantage-established")


def respond(request):
    if not isinstance(request, dict):
        return {"error": "INVALID_REQUEST"}
    op, inp = request.get("operation"), request.get("input") or {}
    if op == "lab.canonical_json":
        return canonical_json(json.loads(inp["text"]))
    if op == "lab.read_json":
        return read_json(inp["text"])
    if op == "lab.forbidden_keys":
        return {"result": forbidden_keys(inp["value"])}
    if op == "agentavow.tool_key":
        return {"result": tool_key(inp["name"])}
    if op == "agentavow.tool_digest":
        return {"result": tool_digest(inp["tool"])}
    if op == "oe08.observation_vantage":
        return vantage(inp["record"], inp["trusted_control_domains"])
    return {"error": "UNSUPPORTED_OPERATION"}


if __name__ == "__main__":
    print(json.dumps(respond(json.loads(sys.stdin.read())), ensure_ascii=False))
