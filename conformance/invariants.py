"""Invariants of the bounded E rule: python -m conformance.invariants.

Two oracle-free checks of ``evaluate``. The first is a set of metamorphic
relations (Chen, Cheung and Yiu, 1998): a transformation of an accepted-evidence
document and the part of the verdict that must not change under it. The second
is differential (McKeeman, 1998): a table-driven reference model of the v0.2
rule, written separately from ``boundary.py``, must agree with it on every
document of an exhaustively generated space. Neither check needs an expected
answer per document, so both reach inputs no committed fixture covers.

Both checks are read-only and touch no fixture. A relation that holds on the
generated space holds on that space; it is not a proof for every input.
"""

import argparse
import itertools
import json
import sys

from .boundary import MINIMUM_CLASSES, InvalidInput, UnsupportedVerification, evaluate

SCOPE = "synthetic-zone-v1/session-1"
OTHER_SCOPE = "synthetic-zone-v1/session-2"
OUTCOMES = ("BLOCKED", "REACHED_EFFECT", "UNKNOWN")
CLASSES = tuple(sorted(MINIMUM_CLASSES)) + ("extra_class",)
OBLIGATION_ORDER = ("credential_topology", "observation_coverage",
                    "minimum_bypass_classes", "attempt_outcomes")


def descriptor(scope):
    return {"scope": scope, "reference": "fixture:accepted-synthetic-premise",
            "revision": "synthetic-model-v1"}


def attempt(cls, outcome, scope=SCOPE):
    return {"class": cls, "scope": scope, "outcome": outcome,
            "reference": f"fixture:{cls}", "revision": "synthetic-model-v1"}


def document(topology, coverage, attempts, scope=SCOPE):
    return {"property": "E",
            "context": {"evaluation_scope": scope,
                        "agent_zone": "synthetic agent roots and import closure; no live credentials",
                        "accepted_topology": topology, "accepted_coverage": coverage},
            "attempts": list(attempts)}


def generated_space(max_attempts=5):
    """Every combination of premise descriptors and attempt sets up to a size.

    Premises: absent, in scope, or in another scope. Attempts: every subset of
    the classes (the five minimum ones plus one extra) up to ``max_attempts``
    members, each member with every outcome, plus one out-of-scope copy of the
    first attempt so scope filtering is exercised in the same space.
    """
    premises = (None, descriptor(SCOPE), descriptor(OTHER_SCOPE))
    for size in range(0, max_attempts + 1):
        for classes in itertools.combinations(CLASSES, size):
            for outcomes in itertools.product(OUTCOMES, repeat=size):
                attempts = [attempt(c, o) for c, o in zip(classes, outcomes)]
                for topology in premises:
                    for coverage in premises:
                        yield document(topology, coverage, attempts)
                        if attempts:
                            yield document(topology, coverage,
                                           attempts + [attempt(classes[0], "REACHED_EFFECT", OTHER_SCOPE)])


def reference_model(doc):
    """A second implementation of SPECIFICATION-v0.2.md section 4, table driven."""
    scope = doc["context"]["evaluation_scope"]
    in_scope = tuple(a for a in doc["attempts"] if a["scope"] == scope)
    facts = {
        "credential_topology": doc["context"]["accepted_topology"] is not None
        and doc["context"]["accepted_topology"]["scope"] == scope,
        "observation_coverage": doc["context"]["accepted_coverage"] is not None
        and doc["context"]["accepted_coverage"]["scope"] == scope,
        "minimum_bypass_classes": MINIMUM_CLASSES.issubset({a["class"] for a in in_scope}),
        "attempt_outcomes": all(a["outcome"] != "UNKNOWN" for a in in_scope),
    }
    bypass = any(a["outcome"] == "REACHED_EFFECT" for a in in_scope)
    if bypass:
        status, obligations = "FAIL", []
    elif all(facts.values()):
        status, obligations = "PASS", []
    else:
        status = "NOT_ESTABLISHED"
        obligations = [name for name in OBLIGATION_ORDER if not facts[name]]
    return {"property": "E", "evaluation_scope": scope, "status": status,
            "unresolved_obligations": obligations}


def _run(doc):
    return evaluate(json.loads(json.dumps(doc)))


def relation_failures(doc):
    """Violations of the metamorphic relations on one document, as labels."""
    failures = []
    base = _run(doc)
    scope = doc["context"]["evaluation_scope"]
    attempts = doc["attempts"]

    # INV-1 the verdict names the property and echoes the scope
    if base["property"] != "E" or base["evaluation_scope"] != scope:
        failures.append("INV-1 envelope")
    if set(base) != {"property", "evaluation_scope", "status", "unresolved_obligations"}:
        failures.append("INV-1 envelope keys")
    # INV-2 determinism and input immutability
    snapshot = json.dumps(doc, sort_keys=True)
    again = _run(doc)
    if again != base or json.dumps(doc, sort_keys=True) != snapshot:
        failures.append("INV-2 determinism")
    # INV-3 attempt order never matters
    for permutation in itertools.islice(itertools.permutations(attempts), 6):
        if _run(document(doc["context"]["accepted_topology"], doc["context"]["accepted_coverage"],
                         permutation, scope)) != base:
            failures.append("INV-3 attempt order")
            break
    # INV-4 an attempt in another scope never matters
    extra = attempt("without_authorization", "REACHED_EFFECT", OTHER_SCOPE)
    if _run({**doc, "attempts": attempts + [extra]}) != base:
        failures.append("INV-4 out-of-scope attempt")
    # INV-5 an observed bypass in scope dominates everything else
    bypass = _run({**doc, "attempts": attempts + [attempt("extracted_callable", "REACHED_EFFECT")]})
    if bypass["status"] != "FAIL" or bypass["unresolved_obligations"]:
        failures.append("INV-5 bypass dominance")
    # INV-6 removing an accepted premise never strengthens the verdict
    for key, obligation in (("accepted_topology", "credential_topology"),
                            ("accepted_coverage", "observation_coverage")):
        weaker = _run({**doc, "context": {**doc["context"], key: None}})
        if base["status"] == "FAIL":
            expected = base
        elif base["status"] == "PASS":
            expected = {**base, "status": "NOT_ESTABLISHED", "unresolved_obligations": [obligation]}
        else:
            expected = {**base, "unresolved_obligations": sorted(
                set(base["unresolved_obligations"]) | {obligation}, key=OBLIGATION_ORDER.index)}
        if weaker != expected:
            failures.append(f"INV-6 premise removal {key}")
    # INV-7 an unknown outcome never yields PASS
    if attempts:
        unknown = [dict(a, outcome="UNKNOWN") if i == 0 else a for i, a in enumerate(attempts)]
        result = _run({**doc, "attempts": unknown})
        if result["status"] == "PASS":
            failures.append("INV-7 unknown outcome")
    # INV-8 PASS needs every minimum class: dropping one in-scope minimum attempt breaks PASS
    if base["status"] == "PASS":
        for i, a in enumerate(attempts):
            if a["scope"] == scope and a["class"] in MINIMUM_CLASSES:
                remaining = attempts[:i] + attempts[i + 1:]
                if MINIMUM_CLASSES.issubset({b["class"] for b in remaining if b["scope"] == scope}):
                    continue
                result = _run({**doc, "attempts": remaining})
                if result["status"] != "NOT_ESTABLISHED" or "minimum_bypass_classes" not in result["unresolved_obligations"]:
                    failures.append("INV-8 minimum classes")
                    break
    # INV-9 obligations are exactly the failed premises, in the declared order, and empty when decisive
    obligations = base["unresolved_obligations"]
    if base["status"] in ("PASS", "FAIL") and obligations:
        failures.append("INV-9 decisive with obligations")
    if base["status"] == "NOT_ESTABLISHED" and (not obligations or obligations != sorted(
            set(obligations), key=OBLIGATION_ORDER.index) or len(set(obligations)) != len(obligations)):
        failures.append("INV-9 obligation set")
    # INV-10 an expected result in the input is refused before inference
    for key in ("expected", "expected_property_verdict", "status"):
        try:
            _run({**doc, key: "PASS"})
        except InvalidInput:
            continue
        failures.append(f"INV-10 expectation in input ({key})")
    # INV-11 another property is a non-verdict, never a verdict
    try:
        _run({**doc, "property": "G"})
        failures.append("INV-11 unsupported property")
    except UnsupportedVerification:
        pass
    # INV-12 differential agreement with the reference model
    if base != reference_model(doc):
        failures.append("INV-12 reference model")
    return failures


def check(space=None):
    """Run every relation over the space; return (documents checked, failures)."""
    checked = 0
    failures = []
    for doc in (space if space is not None else generated_space()):
        checked += 1
        for label in relation_failures(doc):
            failures.append({"document": doc, "relation": label})
    return checked, failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--json", help="write the failures here")
    args = parser.parse_args(argv)
    checked, failures = check(generated_space(args.max_attempts))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(failures, handle, indent=2)
    print(f"{checked} generated documents, 12 relations, {len(failures)} failure(s) (read-only)")
    for item in failures[:20]:
        print(f"  {item['relation']}: {json.dumps(item['document'])[:160]}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
