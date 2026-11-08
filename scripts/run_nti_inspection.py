#!/usr/bin/env python3
"""Reproduce the NTI source-inspection results: python scripts/run_nti_inspection.py.

This executes producer code. It compiles and tests a checkout of
abisheakp197/Neutral-Trust-Infrastructure with AACP-authored test candidates
added, so run it only in a disposable environment. It never edits expectations.

Procedure:
  1. Check the checkout is at the pinned revision and the subject file matches
     its pinned SHA-256. Any mismatch is a non-verdict error.
  2. Baseline: copy docs/nti-source-inspection/reproduction_candidates.rs into
     ube-foundation/tests/ and run it. Every candidate is expected to pass,
     which means every weakness is present.
  3. Discrimination: for each mutation in mutations.json, restore the pristine
     subject file, apply that one repair, and run its named tests. Each is
     expected to FAIL. A build error is recorded as BUILD_ERROR, never as a
     discriminating failure.
  4. Write a result record and exit 0 only if every expectation held.

Usage:
  python scripts/run_nti_inspection.py --nti /path/to/nti-checkout \\
      --out docs/nti-source-inspection/results/<run-id>.json --run-id <run-id>
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import platform
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSPECTION = ROOT / "docs" / "nti-source-inspection"
CANDIDATES = INSPECTION / "reproduction_candidates.rs"
MUTATIONS = INSPECTION / "mutations.json"
EXPECTED = INSPECTION / "expected.json"
PROCEDURE_FILES = (
    "scripts/run_nti_inspection.py",
    "docs/nti-source-inspection/reproduction_candidates.rs",
    "docs/nti-source-inspection/mutations.json",
    "docs/nti-source-inspection/expected.json",
)
TEST_TARGET = "reproduction_candidates"
LINE = re.compile(r"^test (\S+) \.\.\. (ok|FAILED|ignored)$")


class NonVerdict(Exception):
    """The run could not reach a verdict (wrong pin, changed bytes, broken harness)."""


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, cwd):
    proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def tool_version(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True).stdout.strip()
    except OSError:
        return "UNKNOWN"


def cargo_test(crate: pathlib.Path, names=None):
    """Run the candidate test target. Returns (built, {name: status}, canonical_digest)."""
    argv = ["cargo", "test", "--locked", "--test", TEST_TARGET]
    if names:
        argv += ["--", "--exact", "--test-threads=1", *names]
    else:
        argv += ["--", "--test-threads=1"]
    code, out = run(argv, crate)
    statuses = {}
    for raw in out.splitlines():
        m = LINE.match(raw.strip())
        if m:
            statuses[m.group(1)] = m.group(2)
    built = "Running tests/" in out or bool(statuses)
    canonical = "\n".join(sorted(f"{k} {v}" for k, v in statuses.items())) + "\n"
    return built, statuses, hashlib.sha256(canonical.encode()).hexdigest(), code


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nti", type=pathlib.Path, required=True, help="NTI checkout at the pinned revision")
    ap.add_argument("--out", type=pathlib.Path, required=True, help="result record to write")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--operator", default="UNKNOWN", help="who ran this, e.g. a GitHub login or CI")
    ap.add_argument("--independence", default="AUTHOR_RUN",
                    choices=["AUTHOR_RUN", "REPRODUCTION", "SECOND_IMPLEMENTATION", "INDEPENDENT_IMPLEMENTATION"])
    args = ap.parse_args(argv)

    mutations = json.loads(MUTATIONS.read_text())
    expected = json.loads(EXPECTED.read_text())
    subject = mutations["subject"]
    nti = args.nti.resolve()
    crate = nti / "ube-foundation"
    lib = nti / subject["file"]

    record = {
        "schema": "aacp-nti-inspection-result-v1",
        "run_id": args.run_id,
        "started_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "operator": args.operator,
        "independence": args.independence,
        "subject": dict(subject),
        "procedure": {
            "harness": "scripts/run_nti_inspection.py",
            "harness_sha256": sha256_file(pathlib.Path(__file__).resolve()),
            "candidates_sha256": sha256_file(CANDIDATES),
            "mutations_sha256": sha256_file(MUTATIONS),
            "expected_sha256": sha256_file(EXPECTED),
            "aacp_revision": run(["git", "rev-parse", "HEAD"], ROOT)[1].strip() or "UNKNOWN",
            # Fixed repository paths, so a self-test that swaps MUTATIONS for a
            # temporary file is reported as uncommitted rather than crashing.
            "procedure_committed": all(p.resolve().is_relative_to(ROOT) for p in (CANDIDATES, MUTATIONS, EXPECTED))
                                   and run(["git", "status", "--porcelain", "--", *PROCEDURE_FILES], ROOT)[1].strip() == "",
        },
        "environment": {
            "rustc": tool_version(["rustc", "--version"]),
            "cargo": tool_version(["cargo", "--version"]),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "baseline": None,
        "discrimination": [],
        "non_verdict_errors": [],
        "verdict": None,
    }

    pristine = None
    try:
        head = run(["git", "rev-parse", "HEAD"], nti)[1].strip()
        if head != subject["revision"]:
            raise NonVerdict(f"checkout is at {head}, expected {subject['revision']}")
        pristine = lib.read_bytes()
        if hashlib.sha256(pristine).hexdigest() != subject["file_sha256"]:
            raise NonVerdict(f"{subject['file']} bytes differ from the pinned SHA-256")

        shutil.copyfile(CANDIDATES, crate / "tests" / f"{TEST_TARGET}.rs")

        built, statuses, digest, _ = cargo_test(crate)
        if not built:
            raise NonVerdict("baseline did not build")
        want = expected["baseline"]["tests"]
        record["baseline"] = {
            "tests": statuses,
            "canonical_sha256": digest,
            "canonical_form": "sorted '<test> <status>' lines, newline-terminated",
            "met": statuses == want,
            "mismatches": {k: {"expected": v, "observed": statuses.get(k, "MISSING")}
                           for k, v in want.items() if statuses.get(k) != v},
        }
        extra = sorted(set(statuses) - set(want))
        if extra:
            record["baseline"]["unexpected_tests"] = extra
            record["baseline"]["met"] = False

        source = pristine.decode("utf-8")
        for m in mutations["mutations"]:
            entry = {"id": m["id"], "finding": m["finding"], "repair": m["repair"], "tests": {}}
            count = source.count(m["old"])
            if count != 1:
                entry["status"] = "ANCHOR_ERROR"
                entry["detail"] = f"anchor occurs {count} times"
                record["discrimination"].append(entry)
                continue
            lib.write_text(source.replace(m["old"], m["new"]), encoding="utf-8")
            try:
                built, statuses, digest, _ = cargo_test(crate, m["tests"])
            finally:
                lib.write_bytes(pristine)
            if not built:
                entry["status"] = "BUILD_ERROR"
            else:
                entry["tests"] = {t: statuses.get(t, "MISSING") for t in m["tests"]}
                ok = all(v == expected["discrimination"]["expected_status"] for v in entry["tests"].values())
                entry["status"] = "DISCRIMINATES" if ok else "DOES_NOT_DISCRIMINATE"
                entry["canonical_sha256"] = digest
            record["discrimination"].append(entry)

        if hashlib.sha256(lib.read_bytes()).hexdigest() != subject["file_sha256"]:
            raise NonVerdict("subject file was not restored after mutations")
    except NonVerdict as exc:
        record["non_verdict_errors"].append(str(exc))
    finally:
        if pristine is not None:
            lib.write_bytes(pristine)

    met = (not record["non_verdict_errors"] and record["baseline"] and record["baseline"]["met"]
           and record["discrimination"]
           and all(d["status"] == "DISCRIMINATES" for d in record["discrimination"]))
    record["verdict"] = ("EXPECTATIONS_MET" if met else
                         "NON_VERDICT" if record["non_verdict_errors"] else "EXPECTATIONS_NOT_MET")
    record["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"{record['verdict']}: baseline "
          f"{'met' if record['baseline'] and record['baseline']['met'] else 'not met'}, "
          f"{sum(d['status'] == 'DISCRIMINATES' for d in record['discrimination'])}/"
          f"{len(mutations['mutations'])} mutations discriminate -> {args.out}")
    return 0 if met else 1


if __name__ == "__main__":
    sys.exit(main())
