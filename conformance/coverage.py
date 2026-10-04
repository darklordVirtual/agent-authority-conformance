"""Cross-platform coverage checks for the seven REMORA authority properties.

This module deliberately reports a component matrix, not a score.  A platform
can export the existing v0.2 assessment format and use this module to check
that all core properties are represented before comparing the records.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import ValidationError

from .validation import validate_assessment

COMPONENTS = {
    "A": "Receipt Integrity",
    "B": "Authority Provenance",
    "C": "Exact-Call Integrity",
    "D": "Semantic Authority",
    "E": "Execution-Boundary Integrity",
    "F": "TOCTOU Resistance",
    "G": "Effect Verification",
}
COMPONENT_ORDER = tuple(COMPONENTS)


class CoverageError(ValueError):
    """An assessment is valid JSON but cannot represent a complete matrix."""


def component_matrix(document: dict[str, Any]) -> dict[str, Any]:
    """Return a comparable A–G matrix without aggregating its results.

    The assessment schema intentionally permits a subset.  This stricter
    operation is opt-in for interoperability suites that need every component
    to be represented explicitly.
    """
    validate_assessment(document)
    rows = document["properties"]
    by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for row in rows:
        component_id = row["id"]
        if component_id in by_id:
            duplicates.append(component_id)
        by_id[component_id] = row

    missing = [component_id for component_id in COMPONENT_ORDER if component_id not in by_id]
    if duplicates or missing:
        details = []
        if duplicates:
            details.append(f"duplicate component IDs: {', '.join(sorted(set(duplicates)))}")
        if missing:
            details.append(f"missing component IDs: {', '.join(missing)}")
        raise CoverageError("; ".join(details))

    return {
        "system": document["system"],
        "system_version": document["system_version"],
        "revision": document["revision"],
        "components": [
            {
                "id": component_id,
                "property": COMPONENTS[component_id],
                "status": by_id[component_id]["status"],
                "verification_status": by_id[component_id]["verification_status"],
                "evidence_tier": by_id[component_id]["evidence_tier"],
            }
            for component_id in COMPONENT_ORDER
        ],
    }


def _read_documents(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    documents = []
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CoverageError(f"{path}: unable to read JSON assessment: {exc}") from exc
        documents.append((path, document))
    return documents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessments", nargs="+", type=Path)
    parser.add_argument("--report", type=Path, help="write the component matrices as JSON")
    args = parser.parse_args(argv)

    report: list[dict[str, Any]] = []
    failures = []
    for path, document in _read_documents(args.assessments):
        try:
            report.append({"path": str(path), **component_matrix(document)})
        except (CoverageError, ValidationError, KeyError, TypeError) as exc:
            failures.append({"path": str(path), "message": str(exc)})

    if args.report:
        args.report.write_text(json.dumps({"assessments": report, "failures": failures}, indent=2) + "\n",
                               encoding="utf-8")
    if failures:
        for failure in failures:
            print(f"Coverage failed: {failure['path']}: {failure['message']}", file=sys.stderr)
        return 1

    print(f"Checked complete A-G matrices for {len(report)} assessment(s); no aggregate score produced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
