"""Read-only corpus and assessment checks: python -m conformance.check."""

import argparse
import json
import sys
from pathlib import Path

from .boundary import InvalidInput, UnsupportedVerification, evaluate
from .validation import ROOT, validate_assessment


def check_fixture(path):
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if set(fixture) != {"id", "description", "input", "expected"}:
        raise ValueError(f"{path}: invalid fixture envelope")
    # Expectations belong exclusively to the harness, never to evaluate().
    try:
        actual = evaluate(fixture["input"])
    except InvalidInput:
        actual = {"verification_status": "INVALID_INPUT", "status": None}
    except UnsupportedVerification:
        actual = {"verification_status": "UNSUPPORTED", "status": None}
    if actual != fixture["expected"]:
        raise ValueError(
            f"{path} ({fixture['id']}): expected {fixture['expected']!r}, got {actual!r}; "
            "inspect the fixture expectation and verifier input separately"
        )


def corpus_paths(values):
    """Return JSON files from user-supplied files or directories."""
    paths = []
    for value in values:
        path = Path(value)
        if path.is_file() and path.suffix == ".json":
            paths.append(path)
        elif path.is_dir():
            paths.extend(path.rglob("*.json"))
        else:
            raise ValueError(f"Corpus path does not contain JSON data: {path}")
    return sorted(set(paths))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=ROOT / "tests" / "fixtures")
    parser.add_argument(
        "--assessments", nargs="+", type=Path,
        help="assessment files or directories; defaults to the committed example corpora",
    )
    parser.add_argument(
        "--report", type=Path,
        help="write a JSON report containing all validation failures",
    )
    args = parser.parse_args(argv)
    assessment_roots = args.assessments or [ROOT / "examples", ROOT / "tests" / "adversarial"]
    report = {"assessments": [], "fixtures": [], "failures": []}
    try:
        assessments = corpus_paths(assessment_roots)
        if not args.assessments:
            assessments = [
                path for path in assessments
                if path.parent.name != "adversarial" or path.name.startswith("assessment-")
            ]
        fixtures = corpus_paths([args.fixtures])
        if not assessments or not fixtures:
            raise ValueError("Assessment or fixture corpus is empty")
        report["assessments"] = [str(path) for path in assessments]
        report["fixtures"] = [str(path) for path in fixtures]
        for path in assessments:
            try:
                validate_assessment(json.loads(path.read_text(encoding="utf-8")))
            except Exception as exc:
                report["failures"].append({"kind": "assessment", "path": str(path), "message": str(exc)})
        for path in fixtures:
            try:
                check_fixture(path)
            except Exception as exc:
                report["failures"].append({"kind": "fixture", "path": str(path), "message": str(exc)})
    except Exception as exc:
        report["failures"].append({"kind": "runner", "message": str(exc)})
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["failures"]:
        for failure in report["failures"]:
            print(f"Validation failed ({failure['kind']}): {failure.get('path', '<runner>')}: {failure['message']}", file=sys.stderr)
        return 1
    print(f"Validated {len(report['assessments'])} assessments and {len(report['fixtures'])} fixtures (read-only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
