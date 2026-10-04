"""Seeded-fault adequacy of the fixture corpus: python -m conformance.mutations.

Mutation analysis in the sense of DeMillo, Lipton and Sayward (1978): each entry
in ``mutations-v0.2.json`` seeds one small fault into ``boundary.py`` and the
committed fixtures are asked whether they notice. A fault no fixture notices is
a survivor: a gap in the corpus, never a defect in the rule. Whether a survivor
is equivalent to the original rule is undecidable in general (Budd and Angluin,
1982), so an equivalent mutation is declared with its reason and reported, not
scored away.

The harness is read-only. It never writes the mutated source to ``boundary.py``,
never rewrites a fixture, and never feeds an expected result into ``evaluate``.
"""

import argparse
import hashlib
import json
import sys
import types
from pathlib import Path

from .validation import ROOT

DEFINITIONS = ROOT / "conformance" / "mutations-v0.2.json"
SUBJECT = ROOT / "conformance" / "boundary.py"
FIXTURES = ROOT / "tests" / "fixtures"


class HarnessError(RuntimeError):
    """The harness itself is inconsistent; no mutation result is reported."""


def load_definitions(path=DEFINITIONS):
    definitions = json.loads(path.read_text(encoding="utf-8"))
    ids = [m["id"] for m in definitions["mutations"]]
    if len(ids) != len(set(ids)):
        raise HarnessError("duplicate mutation id")
    return definitions


def definitions_digest(path=DEFINITIONS):
    """sha256 of the definitions file, for committing a fault set before a run."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def apply_mutation(source, mutation):
    """The subject's source with exactly one anchor replaced."""
    count = source.count(mutation["anchor"])
    if count != 1:
        raise HarnessError(f"{mutation['id']}: anchor occurs {count} times, expected exactly once")
    return source.replace(mutation["anchor"], mutation["replacement"])


def load_rule(source, name):
    """Compile a variant of boundary.py into a fresh module; nothing touches disk."""
    module = types.ModuleType(f"conformance._mutant_{name}")
    module.__package__ = "conformance"
    module.__file__ = str(SUBJECT)
    exec(compile(source, str(SUBJECT), "exec"), module.__dict__)
    return module


def load_fixtures(directory=FIXTURES):
    fixtures = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))]
    if not fixtures:
        raise HarnessError("fixture corpus is empty")
    return fixtures


def outcome_of(rule, document):
    """What a rule reports for a fixture input, with verifier states as data."""
    try:
        return rule.evaluate(json.loads(json.dumps(document)))
    except rule.InvalidInput:
        return {"verification_status": "INVALID_INPUT", "status": None}
    except rule.UnsupportedVerification:
        return {"verification_status": "UNSUPPORTED", "status": None}
    except Exception as exc:  # the class of an unexpected exception is the finding
        return {"verification_status": "ERROR", "status": None, "raised": type(exc).__name__}


def score(rule, fixtures):
    """Fixture ids whose expected result the rule does not reproduce."""
    return [f["id"] for f in fixtures if outcome_of(rule, f["input"]) != f["expected"]]


def sweep(definitions=None, fixtures=None, source=None):
    definitions = definitions or load_definitions()
    fixtures = fixtures or load_fixtures()
    source = source if source is not None else SUBJECT.read_text(encoding="utf-8")
    original = load_rule(source, "original")
    baseline = score(original, fixtures)
    if baseline:
        raise HarnessError(f"the unmutated rule disagrees with fixtures {baseline}; the sweep would be meaningless")
    rows = []
    for mutation in definitions["mutations"]:
        rule = load_rule(apply_mutation(source, mutation), mutation["id"].replace("-", "_"))
        killed_by = score(rule, fixtures)
        rows.append({
            "id": mutation["id"],
            "class": mutation["class"],
            "control": mutation.get("control"),
            "equivalent": mutation.get("equivalent"),
            "status": "killed" if killed_by else "survived",
            "killed_by": killed_by,
        })
    for row in rows:
        if row["control"] == "positive" and row["status"] != "killed":
            raise HarnessError("the positive control survived; the fixtures cannot see the decision")
        if row["control"] == "inert" and row["status"] != "survived":
            raise HarnessError("the inert control was killed; the harness reacts to a no-op")
    scored = [r for r in rows if not r["control"]]
    survivors = [r["id"] for r in scored if r["status"] == "survived" and not r["equivalent"]]
    equivalent = [r["id"] for r in scored if r["status"] == "survived" and r["equivalent"]]
    return {
        "artifact": definitions["artifact"],
        "definitions_sha256": definitions_digest(),
        "fixtures": len(fixtures),
        "mutations": len(scored),
        "killed": sum(1 for r in scored if r["status"] == "killed"),
        "survived": survivors,
        "declared_equivalent": equivalent,
        "rows": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="write the full report here")
    parser.add_argument("--hash", action="store_true", help="print the definitions digest and exit")
    args = parser.parse_args(argv)
    if args.hash:
        print(definitions_digest())
        return 0
    try:
        report = sweep()
    except HarnessError as exc:
        print(f"Harness error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['mutations']} mutations, {report['killed']} killed, "
          f"{len(report['survived'])} survived, {len(report['declared_equivalent'])} declared equivalent "
          f"(definitions {report['definitions_sha256'][:12]}, {report['fixtures']} fixtures, read-only)")
    for mid in report["survived"]:
        print(f"  survived: {mid}", file=sys.stderr)
    return 1 if report["survived"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
