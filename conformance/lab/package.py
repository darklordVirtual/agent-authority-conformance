"""package: build the delivery package (RUN-PROTOCOL-v0.3 §5.6)."""

import re
import shutil
from pathlib import Path

from . import consent, state
from .canonical import read_json, sha256_file, sha256_json, write_json
from .errors import PackageError
from .report import render_notice, render_report, render_reproduce, render_status

LAB_SRC = Path(__file__).resolve().parent
EXCLUDED_DIRS = frozenset({".git", ".local", "reruns", "__pycache__"})
# Lifecycle files change after delivery; CONSENT.json carries its own hash chain.
MUTABLE = frozenset({"MANIFEST.json", "STATE.json", "CONSENT.json", "STATUS.md", "REVIEW.md"})
EMAIL = "e-mail address"
LEAK_PATTERNS = (
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"), "GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "API key"),
    (re.compile(r"\b(?!git@)[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"), EMAIL),
    (re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|/root/|/Volumes/|/private/var/folders/"
                r"|/var/folders/|(?<![A-Za-z0-9.])/tmp/|[A-Za-z]:[\\/]+Users[\\/]"), "local absolute path"),
)

RERUN_PY = '''#!/usr/bin/env python3
"""Rerun this package from a fresh copy: python3 rerun.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE / "lab"))
from conformance.lab.rerun import main  # noqa: E402

raise SystemExit(main([str(HERE)]))
'''

WORKFLOW = '''name: Rerun
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  rerun:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "{python}"
      - name: Rerun from pinned inputs (CI is not network isolation)
        run: python3 rerun.py
'''


def package_files(root):
    """Files covered by MANIFEST.json."""
    root = Path(root)
    return sorted(p for p in root.rglob("*")
                  if p.is_file() and not (set(p.relative_to(root).parts) & EXCLUDED_DIRS)
                  and p.relative_to(root).as_posix() not in MUTABLE)


def scan_for_leaks(root):
    root, problems = Path(root), []
    for path in package_files(root) + [root / name for name in sorted(MUTABLE) if (root / name).is_file()]:
        rel = path.relative_to(root).as_posix()
        if rel.startswith("lab/"):
            continue  # verbatim copy of the lab source, covered by MANIFEST
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, label in LEAK_PATTERNS:
            if label == EMAIL and rel.startswith("UPSTREAM-LICENSE-"):
                continue  # upstream licence texts may name a contact address
            if pattern.search(text):
                problems.append(f"{rel}: {label}")
    if problems:
        raise PackageError("refusing to package: " + "; ".join(problems))


def write_manifest(root):
    root = Path(root)
    files = {p.relative_to(root).as_posix(): {"sha256": sha256_file(p), "bytes": p.stat().st_size}
             for p in package_files(root)}
    write_json(root / "MANIFEST.json", {
        "scope": "every package file except lifecycle files (" + ", ".join(sorted(MUTABLE)) + ") and reruns/",
        "files": files})


def vendor_lab(run_dir):
    dest = Path(run_dir) / "lab" / "conformance"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(LAB_SRC, dest / "lab", ignore=shutil.ignore_patterns("__pycache__"))
    (dest / "__init__.py").write_text('"""Vendored Agent Authority Conformance lab (Apache-2.0)."""\n',
                                      encoding="utf-8")


def _delivery_records(run_dir):
    records = {}
    engine_dir = Path(run_dir) / "results" / "engine"
    for path in sorted(engine_dir.glob("*.json")) if engine_dir.is_dir() else []:
        entry = read_json(path).get("original_to_delivery")
        if entry:
            records[path.relative_to(run_dir).as_posix()] = entry
    return records


def verify_run_integrity(run_dir, current):
    """Results, scope and run-owned files must be exactly what run produced and froze."""
    from .plan import run_files
    from .runner import results_hashes
    plan = read_json(run_dir / "RUN-PLAN-FROZEN.json")
    problems = []
    if sha256_json(plan["core"]) != current.get("plan_sha256"):
        problems.append("RUN-PLAN-FROZEN.json differs from the frozen plan hash")
    if sha256_file(run_dir / "SCOPE.json") != plan["core"]["scope_sha256"]:
        problems.append("SCOPE.json changed after freeze")
    if run_files(run_dir) != plan["core"]["run_files"]:
        problems.append("faults, controls, adapter or verifier changed after freeze")
    if results_hashes(run_dir) != current.get("results_sha256"):
        problems.append("results/ differ from what run wrote")
    if problems:
        raise PackageError("refusing to package: " + "; ".join(problems))
    return plan


def claim_conditions(run_dir, scope):
    """Conditions from scope confirmations; each must name claims (or rows) of this run."""
    known = {c["id"] for c in scope.get("claims", [])} | {r["id"] for r in scope.get("rows", [])}
    conditions = consent.conditions(consent.load(run_dir))
    unknown = sorted({c for cond in conditions for c in cond["claims"]} - known)
    if unknown:
        raise PackageError("refusing to package: scope conditions name unknown claim(s): " + ", ".join(unknown))
    return conditions


def build(run_dir, now):
    current = state.require(run_dir, "RUN")
    run_dir = Path(run_dir)
    scope = read_json(run_dir / "SCOPE.json")
    plan = verify_run_integrity(run_dir, current)
    conditions = claim_conditions(run_dir, scope)
    vendor_lab(run_dir)
    (run_dir / "rerun.py").write_text(RERUN_PY, encoding="utf-8")
    python = ".".join(plan["environment"]["python"].split(".")[:2])
    workflow = run_dir / ".github" / "workflows" / "rerun.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(WORKFLOW.replace("{python}", python), encoding="utf-8")
    results = {p.relative_to(run_dir).as_posix(): read_json(p)
               for p in sorted((run_dir / "results").rglob("*.json"))}
    (run_dir / "REPORT.md").write_text(render_report(scope, plan, results, conditions,
                                                         current.get("preregistered", True)), encoding="utf-8")
    (run_dir / "STATUS.md").write_text(render_status("PRIVATE"), encoding="utf-8")
    (run_dir / "NOTICE").write_text(render_notice(scope), encoding="utf-8")
    (run_dir / "REPRODUCE.md").write_text(render_reproduce(scope, plan), encoding="utf-8")
    delivery = _delivery_records(run_dir)
    if delivery:
        write_json(run_dir / "ORIGINAL-TO-DELIVERY.json", {
            "note": "Delivery copies differ from retained originals only as described per file.",
            "files": delivery})
    scan_for_leaks(run_dir)
    write_manifest(run_dir)
    state.transition(run_dir, "PACKAGED", now, note="package built")
