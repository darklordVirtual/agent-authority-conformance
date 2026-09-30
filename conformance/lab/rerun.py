"""rerun: fresh fetch, verify, execute, compare (RUN-PROTOCOL-v0.3 §7).

Runs from the package's vendored lab code, so a rerun measures with exactly the
code that produced the results.
"""

import argparse
import platform
import sys
import tempfile
from pathlib import Path

from . import pins, plan
from .canonical import read_json, sha256_file, utc_now, write_json
from .engines.base import identity_for
from .errors import LabError
from .package import MUTABLE, package_files
from .runner import execute
from .scope import load_scope

EXIT = {"REPRODUCED": 0, "DIVERGED": 1, "NOT_REPRODUCIBLE": 2}
NOT_COMPARED = ("results/engine/", "results/cross-check/", "results/agreement.json")


def verify_manifest(pkg):
    path = pkg / "MANIFEST.json"
    if not path.is_file():
        return ["MANIFEST.json is missing"]
    listed = read_json(path)["files"]
    problems = []
    for rel, meta in listed.items():
        file = pkg / rel
        if not file.is_file():
            problems.append(f"missing {rel}")
        elif sha256_file(file) != meta["sha256"]:
            problems.append(f"changed {rel}")
    for file in package_files(pkg):
        rel = file.relative_to(pkg).as_posix()
        if rel not in listed and rel not in MUTABLE:
            problems.append(f"unlisted {rel}")
    return problems


def _comparable(rel, obj):
    if rel == "results/claims.json":
        return {f"{r['input']} / {r['claim']}": [r["execution"], r["result"]] for r in obj["records"]}
    return {"status": obj["status"],
            "controls": {k: v["outcome"] for k, v in obj["controls"].items()},
            **{f"mutant {m['fault_id']}": [m["outcome"], m["moved"], m["crashed"]] for m in obj["mutants"]}}


def compare(recorded, fresh):
    keep = lambda d: {k: v for k, v in d.items() if k.startswith("results/") and not k.startswith(NOT_COMPARED)}
    recorded, fresh = keep(recorded), keep(fresh)
    diffs = []
    for rel in sorted(set(recorded) | set(fresh)):
        if rel not in recorded or rel not in fresh:
            diffs.append({"file": rel, "problem": "present on one side only"})
            continue
        a, b = _comparable(rel, recorded[rel]), _comparable(rel, fresh[rel])
        diffs.extend({"file": rel, "item": key, "recorded": a.get(key), "rerun": b.get(key)}
                     for key in sorted(set(a) | set(b)) if a.get(key) != b.get(key))
    return diffs


def rerun(pkg, workdir=None):
    pkg = Path(pkg).resolve()
    problems = verify_manifest(pkg)
    if problems:
        return "NOT_REPRODUCIBLE", {"problems": problems}
    warnings = []
    try:
        scope = load_scope(pkg, require_pins=True)
        recorded_plan = read_json(pkg / plan.FILE)
    except LabError as exc:
        return "NOT_REPRODUCIBLE", {"problems": [str(exc)]}
    recorded_python = recorded_plan["environment"]["python"]
    if platform.python_version().rsplit(".", 1)[0] != recorded_python.rsplit(".", 1)[0]:
        warnings.append(f"Python {platform.python_version()} differs from the recorded {recorded_python}")
    with tempfile.TemporaryDirectory(prefix="aac-rerun-", dir=workdir) as tmp:
        try:
            trees, _ = pins.materialize(scope, tmp)
            fresh_plan = plan.build_plan(pkg, scope, trees, identity_for(scope))
            if plan.plan_hash(fresh_plan) != plan.plan_hash(recorded_plan):
                return "NOT_REPRODUCIBLE", {"problems": ["recomputed plan hash differs from RUN-PLAN-FROZEN.json"],
                                            "warnings": warnings}
            fresh = execute(pkg, scope, trees)
        except LabError as exc:
            return "NOT_REPRODUCIBLE", {"problems": [str(exc)], "warnings": warnings}
    recorded = {p.relative_to(pkg).as_posix(): read_json(p) for p in sorted((pkg / "results").rglob("*.json"))}
    diffs = compare(recorded, fresh)
    return ("DIVERGED" if diffs else "REPRODUCED"), {"diffs": diffs, "warnings": warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rerun a lab package from its pinned inputs.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args(argv)
    outcome, details = rerun(args.package)
    at = utc_now()
    record = {"outcome": outcome, "at": at, "python": platform.python_version(), **details}
    write_json(Path(args.package) / "reruns" / f"rerun-{at.replace(':', '')}.json", record)
    print(outcome)
    for key in ("warnings", "problems", "diffs"):
        for item in details.get(key, []):
            print(f"{key[:-1]}: {item}", file=sys.stderr)
    return EXIT[outcome]
