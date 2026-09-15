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
        raise ValueError(f"{path}: expected {fixture['expected']!r}, got {actual!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=ROOT / "tests" / "fixtures")
    args = parser.parse_args(argv)
    try:
        assessments = sorted((ROOT / "examples").rglob("*.json"))
        fixtures = sorted(args.fixtures.glob("*.json"))
        if not assessments or not fixtures:
            raise ValueError("Assessment or fixture corpus is empty")
        for path in assessments:
            validate_assessment(json.loads(path.read_text(encoding="utf-8")))
        for path in fixtures:
            check_fixture(path)
    except Exception as exc:
        # A failure terminates the harness; it never becomes NOT_ESTABLISHED.
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated {len(assessments)} assessments and {len(fixtures)} fixtures (read-only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
