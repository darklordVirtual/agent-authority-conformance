#!/usr/bin/env python3
"""Write RECORD.json for a measured verification run, next to the run skeleton it came from.

A record is what one runner observed at fixed pins with a fixed verifier and scope: the
subject pins, the public-boundary digest, the run-owned file hashes, the SHA-256 of the
skeleton's SCOPE.json and every claim and probe record exactly as the lab wrote them. It is
not a producer expectation and not a vector suite. Tests compare a fresh run against it, so a
change to the verifier or the skeleton scope requires a new record, never an edit.

Usage: python scripts/record_lab_run.py runs/<run_id> templates/runs/<name>/SCOPE.json
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conformance.lab.canonical import read_json, sha256_file, write_json  # noqa: E402
from conformance.lab.errors import LabError  # noqa: E402
from conformance.lab.package import verify_run_integrity  # noqa: E402
from conformance.lab.state import load_state  # noqa: E402

NOTE = ("What this runner observed at these pins with this verifier and skeleton scope. Not producer "
        "expectations and not a vector suite. A run that differs is a new record, never an edit to this one.")


def build(run_dir, template):
    run_dir, template = Path(run_dir), Path(template)
    current = load_state(run_dir)
    if current["state"] in ("SCOPED", "FROZEN"):
        raise LabError(f"{run_dir.name} has no results yet ({current['state']})")
    plan = verify_run_integrity(run_dir, current)
    scope = read_json(run_dir / "SCOPE.json")
    record = {
        "note": NOTE,
        "run_id": scope["run_id"],
        "template_scope_sha256": sha256_file(template),
        "run_files": plan["core"]["run_files"],
        "subjects": [{"repo": s["repo"], "commit": s["commit"], "files_sha256": s["files_sha256"]}
                     for s in scope["subjects"]],
        "claims": read_json(run_dir / "results" / "claims.json")["records"],
    }
    if "public_boundary" in scope:
        record["public_boundary"] = {k: scope["public_boundary"][k] for k in ("repo", "commit", "path", "sha256")}
    probes = run_dir / "results" / "probes.json"
    if probes.is_file():
        record["probes"] = read_json(probes)["records"]
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("template", type=Path, help="the skeleton SCOPE.json the run was initialised from")
    args = parser.parse_args(argv)
    try:
        record = build(args.run_dir, args.template)
    except LabError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    out = args.template.parent / "recorded" / "RECORD.json"
    write_json(out, record)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
