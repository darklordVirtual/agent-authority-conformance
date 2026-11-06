#!/usr/bin/env python3
"""Build the frozen AACP reference vectors (aacp-reference-vectors-v1).

    python scripts/build_reference_vectors.py --check   # rebuild in memory, compare bytes
    python scripts/build_reference_vectors.py --write   # create v1; refuses if it exists

Every expected answer comes from one of three places, and each vector names
which in ``expected_source``:

* a committed, hand-authored fixture or producer artifact, copied verbatim;
* a producer's signed or published expectation (the AgentAvow fixture);
* the normative text of a specification or profile, written out here by hand.

This script never imports the reference rules (``conformance.boundary``,
``conformance.coverage``, ``conformance.observed_effect_vantage``,
``conformance.agentavow_tool_binding``, ``conformance.lab.canonical``). An
expectation computed by the implementation it is meant to check would test
nothing. ``python -m conformance.vectors check`` then runs the reference
against the frozen expectations, separately.

A frozen version is never rewritten. A change to any source, or to any
expectation, makes ``--check`` fail; the remedy is a new suite version, not an
edit to v1.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = "aacp-reference-vectors-v1"
OUT = ROOT / "vectors" / SUITE


def dumps(obj) -> bytes:
    """The suite's own file form: sorted keys, two-space indent, UTF-8, final newline."""
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def vector(vid, description, inp, expected, source, compare=None):
    out = {"id": vid, "description": description, "input": inp,
           "expected": expected, "expected_source": source}
    if compare is not None:
        out["compare"] = compare
    return out


# ── e_rule.evaluate: the committed fixtures, verbatim ─────────────────────────


def e_rule():
    vectors = []
    for path in sorted((ROOT / "tests" / "fixtures").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT).as_posix()
        vectors.append(vector(
            f"e-{fixture['id']}", fixture["description"], fixture["input"],
            {"result": fixture["expected"]},
            f"fixture:{rel} (hand-authored; expectation copied verbatim)"))
    return {
        "operation": "e_rule.evaluate",
        "specification": "SPECIFICATION-v0.2.md section 6, bounded reference rule for property E",
        "contract": (
            "Input is an execution-boundary-input-v0.2 document "
            "(schema/execution-boundary-input-v0.2.schema.json). The result is the verdict "
            "object. A document the schema refuses yields "
            "{\"verification_status\": \"INVALID_INPUT\", \"status\": null}; a valid document "
            "for a property other than E yields "
            "{\"verification_status\": \"UNSUPPORTED\", \"status\": null}. Both are "
            "non-verdicts returned as results, exactly as the fixtures state them."),
        "vectors": vectors,
    }


# ── oe08.observation_vantage: the producer case and the profile's discriminators ──

PROFILE = "profiles/AACP-OBSERVED-EFFECT-VANTAGE-1.md"
NE, EST, INV = "NOT_ESTABLISHED", "ESTABLISHED", "INVALID_INPUT"
NOT_INDEP = "authoritative-vantage-not-independent"
NOT_EST = "observation-vantage-not-established"


def _ext(**over):
    base = {"observer_id": "verifier", "observed_party": "agent",
            "control_domain": "verifier-domain", "observed_control_domain": "agent-domain",
            "can_observed_party_forge": False, "can_observed_party_suppress": False}
    base.update(over)
    return {k: v for k, v in base.items() if v is not ...}


def oe08():
    case = read("interop/fixtures/rfc189-oe-08-self-vantage.json")
    v = [vector(
        "oe08-producer-self-vantage-claiming-independence",
        "The pinned RFC189 OE-08 producer case: self-vantage that declares independence.",
        {"record": case["input"],
         "trusted_control_domains": case["runner_trust"]["trusted_control_domains"]},
        {"result": case["expected"]},
        "producer:interop/fixtures/rfc189-oe-08-self-vantage.json (expected and the "
        "producer's native_expected not_established/observation_vantage, verbatim)",
        compare=["result", "unmet_obligation", "reason"])]
    rows = [
        ("oe08-self-vantage-trusted-label",
         "Self-vantage with a nominally different, trusted control-domain label (rule 1).",
         {**case["input"], "control_domain": "nominally-external-domain"},
         ["nominally-external-domain"], NE, "observation_vantage", NOT_INDEP),
        ("oe08-independent-trusted-domain",
         "External observer, distinct trusted domain, explicit no-forge and no-suppress (rule 4).",
         _ext(declared_independence=True), ["verifier-domain"], EST, None,
         "independent-vantage-established"),
        ("oe08-independent-without-runner-trust",
         "The same record with no runner-owned trust material: not established (rule 4).",
         _ext(declared_independence=True), [], NE, "observation_vantage", NOT_EST),
        ("oe08-shared-control-domain",
         "External observer in the observed party's control domain (rule 3).",
         _ext(control_domain="shared-domain", observed_control_domain="shared-domain"),
         ["shared-domain"], NE, "observation_vantage", NOT_INDEP),
        ("oe08-untrusted-domain",
         "External observer in a distinct domain the runner does not trust (rule 4).",
         _ext(), ["some-other-domain"], NE, "observation_vantage", NOT_EST),
        ("oe08-observed-party-can-forge",
         "The observed party can forge the observation (rule 2).",
         _ext(can_observed_party_forge=True), ["verifier-domain"], NE,
         "observation_vantage", NOT_INDEP),
        ("oe08-observed-party-can-suppress",
         "The observed party can suppress the observation (rule 2).",
         _ext(can_observed_party_suppress=True), ["verifier-domain"], NE,
         "observation_vantage", NOT_INDEP),
        ("oe08-forge-and-suppress-facts-missing",
         "Distinct trusted domain, but no explicit forge/suppress facts: missing evidence (rule 5).",
         _ext(can_observed_party_forge=..., can_observed_party_suppress=...),
         ["verifier-domain"], NE, "observation_vantage", NOT_EST),
        ("oe08-one-negative-fact-missing",
         "Distinct trusted domain, no-forge stated, suppress fact missing (rules 4 and 5).",
         _ext(can_observed_party_suppress=...), ["verifier-domain"], NE,
         "observation_vantage", NOT_EST),
        ("oe08-control-domain-missing",
         "External observer with no control_domain (rule 5).",
         _ext(control_domain=...), ["verifier-domain"], NE, "observation_vantage", NOT_EST),
        ("oe08-malformed-declared-independence",
         "declared_independence is the string \"true\": malformed typed input (rule 5).",
         {**case["input"], "declared_independence": "true"}, [], INV, None, None),
        ("oe08-malformed-forge-fact",
         "can_observed_party_forge is the integer 0: malformed typed input (rule 5).",
         _ext(can_observed_party_forge=0), ["verifier-domain"], INV, None, None),
        ("oe08-blank-observer",
         "observer_id is blank: the record names no observer (rule 5).",
         _ext(observer_id="  "), ["verifier-domain"], INV, None, None),
        ("oe08-record-not-an-object",
         "The record is a list, not an object (rule 5).",
         ["observer_id", "agent"], [], INV, None, None),
    ]
    for vid, desc, record, trust, result, unmet, reason in rows:
        expected = {"result": result, "unmet_obligation": unmet}
        compare = ["result", "unmet_obligation"]
        if reason is not None:
            expected["reason"] = reason
        v.append(vector(vid, desc, {"record": record, "trusted_control_domains": trust},
                        {"result": expected},
                        f"specification:{PROFILE} 'Procedure' and 'Required discriminators' "
                        "(written out by hand)", compare=compare))
    return {
        "operation": "oe08.observation_vantage",
        "specification": PROFILE,
        "contract": (
            "Input is {record, trusted_control_domains}; trust material is runner-owned and "
            "never read from the record. The result is {result, unmet_obligation, reason}. "
            "Compare only the keys a vector lists in `compare`: the profile fixes result and "
            "unmet_obligation, and keeps reason wording normative only for the OE-08 "
            "discriminator."),
        "vectors": v,
    }


# ── agentavow: the producer's published key pairs, signed digests and vectors ──

AVOW = "interop/fixtures/agentavow-tool-manifest-digest-v1.json"


def _b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def avow_key():
    fixture = read(AVOW)
    return {
        "operation": "agentavow.tool_key",
        "specification": f"{AVOW} derivation.tool_key (AgentAvow v1)",
        "contract": "Input is {name}. The result is the map key string \"tool:...\".",
        "vectors": [vector(f"avow-key-{i:02d}", f"Key encoding of {pair['name']!r}.",
                           {"name": pair["name"]}, {"result": pair["key"]},
                           f"producer:{AVOW} key_encoding[{i}] (verbatim)")
                    for i, pair in enumerate(fixture["key_encoding"])],
    }


def avow_digest():
    fixture = read(AVOW)
    payload = json.loads(_b64url(fixture["attestation"]["jws"].split(".")[1]))
    signed = payload["scan"]["toolDigests"]
    out = []
    for tool in fixture["observed_tools"]:
        key = "tool:" + tool["name"]  # plain ASCII names: the key encoding leaves them as-is
        out.append(vector(
            f"avow-digest-{tool['name']}",
            f"Definition digest of the served tool {tool['name']!r}; _meta is never hashed.",
            {"tool": tool}, {"result": signed[key]},
            f"producer:{AVOW} attestation.jws payload scan.toolDigests[{key!r}] "
            "(issuer-signed)"))
    drifted = copy.deepcopy(fixture["observed_tools"][0])
    drifted["_meta"] = {"injected": "never hashed"}
    drifted["x-unknown"] = "never hashed"
    out.append(vector(
        "avow-digest-meta-and-unknown-fields-ignored",
        "The first tool with _meta changed and an unknown field added: the digest is unchanged.",
        {"tool": drifted}, {"result": signed["tool:" + drifted["name"]]},
        f"producer:{AVOW} derivation.tool_digest ('_meta and unknown fields are never hashed') "
        "and the issuer-signed digest of the unmodified definition"))
    return {
        "operation": "agentavow.tool_digest",
        "specification": f"{AVOW} derivation.tool_digest (AgentAvow v1)",
        "contract": ("Input is {tool}, a served MCP tool definition. The result is "
                     "\"sha256:\" + hex digest of the JCS form of {profile, tool restricted to "
                     "name, title, description, inputSchema, outputSchema, annotations}."),
        "vectors": out,
    }


def avow_binding():
    fixture = read(AVOW)
    trust = {"issuer": fixture["issuer"], "attestation": {"jws": fixture["attestation"]["jws"]}}
    out = []
    for i, v in enumerate(fixture["vectors"]):
        gate = {k: v[k] for k in ("gate", "jws")}
        out.append(vector(f"avow-binding-{v['name']}", v["note"],
                          {"vector": gate, "fixture": trust}, {"result": v["expect"]},
                          f"producer:{AVOW} vectors[{i}].expect (verbatim)"))
    return {
        "operation": "agentavow.binding",
        "specification": f"{AVOW} (AgentAvow tool-manifest-digest-v1, E1 per-tool binding)",
        "contract": (
            "Input is {vector: {gate, jws}, fixture: {issuer, attestation}}; jws is the compact "
            "JWS or \"reference\" for fixture.attestation.jws. The result is the six axes and "
            "rely, as the producer states them. Needs Ed25519 verification."),
        "vectors": out,
    }


# ── lab.canonical_json: the lab's hashing form, written out by hand ───────────

CANON_RULE = (
    "The lab hashes json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) plus a "
    "final newline, encoded as UTF-8 (conformance/lab/canonical.py). This is NOT RFC 8785: "
    "keys sort by code point, non-ASCII is literal, numbers use Python's repr. A verifier "
    "of a lab package digest must reproduce these bytes exactly.")

CANON_CASES = [
    ("canon-empty-object", "An empty object.", {}, "{}\n"),
    ("canon-empty-array", "An empty array at the top level.", [], "[]\n"),
    ("canon-key-order", "Keys are sorted.", {"b": 1, "a": 2},
     '{\n  "a": 2,\n  "b": 1\n}\n'),
    ("canon-nesting", "Nested containers, an empty array, null, booleans.",
     {"z": [], "y": {"x": [1, {"w": None}], "v": True, "u": False}},
     '{\n  "y": {\n    "u": false,\n    "v": true,\n    "x": [\n      1,\n      {\n'
     '        "w": null\n      }\n    ]\n  },\n  "z": []\n}\n'),
    ("canon-non-ascii-literal", "Non-ASCII stays literal UTF-8, including a non-BMP character.",
     {"name": "héllo 🙂"}, '{\n  "name": "héllo 🙂"\n}\n'),
    ("canon-escapes", "Quote, backslash, newline, tab and a control character are escaped.",
     {"s": "q\" b\\ n\n t\t c\u0001"}, '{\n  "s": "q\\" b\\\\ n\\n t\\t c\\u0001"\n}\n'),
    ("canon-line-separator-literal", "U+2028 is not escaped.", {"s": "a b"},
     '{\n  "s": "a b"\n}\n'),
    ("canon-key-order-code-point",
     "U+FFFF sorts before U+1F600 by code point; RFC 8785 (UTF-16 order) would reverse them.",
     {"\U0001F600": 2, "￿": 1}, '{\n  "￿": 1,\n  "\U0001F600": 2\n}\n'),
    ("canon-key-order-case", "Upper case sorts before lower case.", {"a": 1, "B": 2},
     '{\n  "B": 2,\n  "a": 1\n}\n'),
    ("canon-large-integer", "An integer beyond 2^53 is written in full.",
     {"n": 12345678901234567890}, '{\n  "n": 12345678901234567890\n}\n'),
    ("canon-float-forms",
     "Floats use Python's repr: 1.0 keeps its .0, 1e100 is 1e+100, 0.1 is 0.1, -0.0 keeps its sign.",
     {"a": 1.0, "b": 1e100, "c": 0.1, "d": -0.0}, '{\n  "a": 1.0,\n  "b": 1e+100,\n'
     '  "c": 0.1,\n  "d": -0.0\n}\n'),
]


def canonical_json():
    out = []
    for vid, desc, obj, text in CANON_CASES:
        data = text.encode("utf-8")
        # The input is JSON text in the case's own key order (ASCII escapes): the vector
        # files sort their keys, so a parsed value would hide an implementation that
        # never sorts (found by tests/test_vectors_adequacy.py, unsorted-keys).
        source_text = json.dumps(obj, ensure_ascii=True)
        out.append(vector(vid, desc, {"text": source_text},
                          {"result": {"canonical_utf8": text, "sha256": sha256_hex(data)}},
                          "specification:conformance/lab/canonical.py dumps() rule, bytes "
                          "written out by hand; sha256 of those bytes"))
    return {"operation": "lab.canonical_json", "specification": "conformance/lab/canonical.py",
            "contract": CANON_RULE + (" Input is {text}, a JSON document in its own key order; "
                                      "parse it and canonicalize the value. The result is "
                                      "{canonical_utf8, sha256}."), "vectors": out}


# ── lab.read_json: strict reading of a lab file ──────────────────────────────


def read_json():
    rows = [
        ("read-valid", "A well-formed object.", '{"a": 1, "b": [true, null]}',
         {"result": {"a": 1, "b": [True, None]}}),
        ("read-duplicate-top-level", "A key repeated at the top level is refused.",
         '{"a": 1, "a": 2}', {"error": "DUPLICATE_KEY"}),
        ("read-duplicate-nested", "A key repeated inside a nested object is refused.",
         '{"a": {"x": 1, "x": 1}}', {"error": "DUPLICATE_KEY"}),
        ("read-same-key-different-objects", "The same key in two sibling objects is fine.",
         '[{"x": 1}, {"x": 2}]', {"result": [{"x": 1}, {"x": 2}]}),
        ("read-not-json", "Text that is not JSON is refused.", '{"a": 1,}',
         {"error": "INVALID_JSON"}),
    ]
    return {
        "operation": "lab.read_json",
        "specification": "conformance/lab/canonical.py read_json()",
        "contract": ("Input is {text}. The result is the parsed value; a repeated key in any "
                     "object is {\"error\": \"DUPLICATE_KEY\"}, text that is not JSON is "
                     "{\"error\": \"INVALID_JSON\"}."),
        "vectors": [vector(vid, desc, {"text": text}, exp,
                           "specification:conformance/lab/canonical.py read_json() "
                           "(duplicate keys refused), written out by hand")
                    for vid, desc, text, exp in rows],
    }


# ── lab.forbidden_keys: the no-aggregate rule ────────────────────────────────


def forbidden_keys():
    rows = [
        ("agg-none", "No aggregate-like key anywhere.", {"A": {"status": "PASS"}}, []),
        ("agg-top-level-score", "A score at the top level.", {"score": 5}, ["$.score"]),
        ("agg-nested-and-listed",
         "Aggregate keys nested in an object and inside a list, in file order.",
         {"rows": [{"id": "A"}, {"total": 7}], "meta": {"overall": "ok", "grade": "B"}},
         ["$.meta.grade", "$.meta.overall", "$.rows[1].total"]),
        ("agg-every-name", "All five names: overall, score, total, aggregate, grade.",
         {"overall": 1, "score": 1, "total": 1, "aggregate": 1, "grade": 1},
         ["$.aggregate", "$.grade", "$.overall", "$.score", "$.total"]),
        ("agg-value-is-not-a-key", "The words as values or in other keys are not refused.",
         {"note": "score", "scoreboard": 1, "Total": 1}, []),
    ]
    return {
        "operation": "lab.forbidden_keys",
        "specification": "CHARTER.md (no aggregate score) and conformance/lab/canonical.py "
                         "FORBIDDEN_KEYS",
        "contract": ("Input is {value}. The result is the list of JSONPath-like locations "
                     "($.key, [i]) of every key named overall, score, total, aggregate or "
                     "grade. The order is the order of the vector file, whose keys are sorted; "
                     "compare the list as a set if your parser does not keep key order."),
        "vectors": [vector(vid, desc, {"value": value}, {"result": paths},
                           "specification:CHARTER.md and FORBIDDEN_KEYS, written out by hand")
                    for vid, desc, value, paths in rows],
    }


# ── coverage.component_matrix: the strict A-G projection ─────────────────────

NAMES = {"A": "Receipt Integrity", "B": "Authority Provenance", "C": "Exact-Call Integrity",
         "D": "Semantic Authority", "E": "Execution-Boundary Integrity",
         "F": "TOCTOU Resistance", "G": "Effect Verification"}


def _project(doc):
    rows = {r["id"]: r for r in doc["properties"]}
    return {"system": doc["system"], "system_version": doc["system_version"],
            "revision": doc["revision"],
            "components": [{"id": c, "property": NAMES[c], "status": rows[c]["status"],
                            "verification_status": rows[c]["verification_status"],
                            "evidence_tier": rows[c]["evidence_tier"]} for c in NAMES]}


def coverage():
    out = []
    for name in ("pass", "fail", "untested"):
        rel = f"tests/adversarial/assessment-{name}.json"
        doc = read(rel)
        out.append(vector(f"cov-{name}", f"The committed {name} assessment, every A-G row.",
                          {"assessment": doc}, {"result": _project(doc)},
                          f"fixture:{rel} (rows projected one per A-G in order, as README.md "
                          "'cross-platform runs' states; no score)"))
    base = read("tests/adversarial/assessment-pass.json")
    missing = copy.deepcopy(base)
    missing["properties"] = [r for r in missing["properties"] if r["id"] != "G"]
    dup = copy.deepcopy(base)
    dup["properties"].append(copy.deepcopy(dup["properties"][0]))
    invalid = copy.deepcopy(base)
    del invalid["system"]
    for vid, desc, doc, err in [
            ("cov-missing-component", "The pass assessment without its G row.", missing,
             "COVERAGE_ERROR"),
            ("cov-duplicate-component",
             "The pass assessment with its A row twice: the v0.2 schema allows each component "
             "at most once (maxContains 1, maxItems 7), so the schema refuses it first.", dup,
             "INVALID_ASSESSMENT"),
            ("cov-invalid-assessment", "The pass assessment without its system field.",
             invalid, "INVALID_ASSESSMENT")]:
        out.append(vector(vid, desc, {"assessment": doc}, {"error": err},
                          "specification:schema/assessment-v0.2.schema.json and README.md "
                          "'cross-platform runs', written out by hand"))
    return {
        "operation": "coverage.component_matrix",
        "specification": "README.md 'cross-platform runs'; schema/assessment-v0.2.schema.json",
        "contract": ("Input is {assessment}, a v0.2 assessment. The result is {system, "
                     "system_version, revision, components: one row per A-G in order with "
                     "id, property, status, verification_status, evidence_tier}. A missing "
                     "component is {\"error\": \"COVERAGE_ERROR\"}; a document the v0.2 schema "
                     "refuses, including one that repeats a component, is "
                     "{\"error\": \"INVALID_ASSESSMENT\"}. There is no score."),
        "vectors": out,
    }


BUILDERS = [e_rule, oe08, avow_key, avow_digest, avow_binding, canonical_json, read_json,
            forbidden_keys, coverage]


def build() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    entries = []
    seen = set()
    for builder in BUILDERS:
        body = builder()
        for v in body["vectors"]:
            if v["id"] in seen:
                raise SystemExit(f"duplicate vector id {v['id']}")
            seen.add(v["id"])
        doc = {"suite": SUITE, **body}
        name = body["operation"] + ".json"
        data = dumps(doc)
        files[name] = data
        entries.append({"path": name, "operation": body["operation"],
                        "vector_ids": [v["id"] for v in body["vectors"]],
                        "sha256": sha256_hex(data)})
    manifest = {
        "suite": SUITE,
        "status": "frozen",
        "file_form": "sorted keys, two-space indent, UTF-8, final newline",
        "protocol": "docs/REFERENCE-VECTORS.md",
        "files": entries,
    }
    files["MANIFEST.json"] = dumps(manifest)
    sums = [f"{sha256_hex(files[e['path']])}  {e['path']}" for e in entries]
    sums.append(f"{sha256_hex(files['MANIFEST.json'])}  MANIFEST.json")
    files["SHA256SUMS"] = ("\n".join(sums) + "\n").encode("ascii")
    return files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    files = build()
    if args.write:
        if OUT.exists():
            print(f"[REFUSED] {OUT.relative_to(ROOT)} exists; a frozen suite is never "
                  "rewritten. Make a new version instead.", file=sys.stderr)
            return 1
        OUT.mkdir(parents=True)
        for name, data in files.items():
            (OUT / name).write_bytes(data)
        print(f"[WRITE] {OUT.relative_to(ROOT)}: {len(files)} files")
        return 0
    problems = []
    committed = {p.name for p in OUT.iterdir()} if OUT.is_dir() else set()
    for name, data in files.items():
        path = OUT / name
        if not path.is_file():
            problems.append(f"missing {name}")
        elif path.read_bytes() != data:
            problems.append(f"{name} differs from its sources")
    for extra in sorted(committed - set(files) - {"README.md"}):
        problems.append(f"unexpected file {extra}")
    if problems:
        print("[FAIL] the frozen suite no longer reproduces from its sources:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print("A changed source or expectation needs a new suite version, not an edit to "
              f"{SUITE}.", file=sys.stderr)
        return 1
    print(f"[OK] {SUITE} reproduces from its sources ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
