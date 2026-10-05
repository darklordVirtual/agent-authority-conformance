"""RUN-PLAN-FROZEN.json and the freeze gate (RUN-PROTOCOL-v0.3 P2).

The plan hash covers the plan's `core` only. `environment` (Python version) is
recorded for the report and compared as a warning on rerun, never hashed.
"""

import ast
import platform
import sys
from pathlib import Path

from . import LAB_VERSION, consent, state
from .canonical import read_json, sha256_file, sha256_json, utc_now, write_json
from .errors import GateError, PlanError
from .faults import apply_mutation, read_source, row_mutations

FILE = "RUN-PLAN-FROZEN.json"
RUN_OWNED = ("faults", "controls", "adapter", "verifier")
RUN_OWNED_FILES = ("producer-expected.json",)


def run_files(run_dir):
    """Every run-owned input file with its hash."""
    run_dir, out = Path(run_dir), {}
    for sub in RUN_OWNED:
        base = run_dir / sub
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    out[path.relative_to(run_dir).as_posix()] = sha256_file(path)
    for name in RUN_OWNED_FILES:
        if (run_dir / name).is_file():
            out[name] = sha256_file(run_dir / name)
    return out


def check_mutations(tree, mutations):
    problems = []
    for mutation in mutations:
        path = Path(tree) / mutation["file"]
        if not path.is_file():
            problems.append(f"{mutation['id']}: {mutation['file']} is not in the pinned tree")
            continue
        try:
            mutated = apply_mutation(read_source(path), mutation)
            if path.suffix == ".py":
                ast.parse(mutated)
        except PlanError as exc:
            problems.append(str(exc))
        except SyntaxError as exc:
            problems.append(f"{mutation['id']}: replacement does not parse: {exc.msg}")
    if problems:
        raise PlanError("; ".join(problems))


def build_plan(run_dir, scope, trees, engine_identity):
    core = {
        "lab_version": LAB_VERSION,
        "run_id": scope["run_id"],
        "kind": scope["kind"],
        "scope_sha256": sha256_file(Path(run_dir) / "SCOPE.json"),
        "subjects": [{"repo": s["repo"], "commit": s["commit"], "files_sha256": s["files_sha256"]}
                     for s in scope["subjects"]],
        "run_files": run_files(run_dir),
        "engine": engine_identity,
    }
    if scope["kind"] == "adequacy":
        rows = []
        for row in scope["rows"]:
            controls, faults = row_mutations(run_dir, scope, row)
            check_mutations(trees[0], [controls["positive"], controls["inert"], *faults])
            rows.append({"id": row["id"], "controls": [controls["positive"]["id"], controls["inert"]["id"]],
                         "faults": [f["id"] for f in faults]})
        core["rows"] = rows
    return {"core": core,
            "environment": {"python": platform.python_version(), "implementation": sys.implementation.name}}


def plan_hash(plan):
    return sha256_json(plan["core"])


def require_agreement(run_dir, scope, now=None, workdir=None):
    """Manual: every agreement party agreed the scope and authorised the run.
    Self-service: the producer's offer is still listed, unrevoked and unexpired."""
    if scope.get("track", "manual") == "self_service":
        from .offer import check_tip, verify_scope_offer
        consent.load(run_dir)  # the log may hold reviews or declines; it must still verify
        verify_scope_offer(scope, workdir)
        check_tip(scope["offer"], now or utc_now(), workdir)
        return
    if not (isinstance(scope.get("agreement_ref"), str) and scope["agreement_ref"].startswith("https://")):
        raise GateError("agreement_ref must link the issue or comment where the scope was agreed")
    events = consent.load(run_dir)
    withdrew = consent.withdrawn_parties(events, scope["agreement_parties"])
    if withdrew:
        raise GateError(f"{', '.join(withdrew)} withdrew; this run cannot proceed (start a new run)")
    for action in ("scope_agreed", "run_authorized"):
        done = {consent.handle(e["who"]) for e in events if e["action"] == action}
        missing = sorted(p for p in scope["agreement_parties"] if consent.handle(p) not in done)
        if missing:
            raise GateError(f"{action} is missing from: {', '.join(missing)}")


def freeze(run_dir, scope, trees, engine_identity, now, published_ref=None, not_preregistered=False):
    """First call writes the plan and returns its hash. Publish the hash, then call
    again with published_ref to move to FROZEN. Returns (hash, frozen).

    Self-service runs may instead freeze without publishing the hash first
    (not_preregistered); the report then says the plan was not preregistered."""
    current = state.require(run_dir, "SCOPED")
    self_service = scope.get("track", "manual") == "self_service"
    if not_preregistered and not self_service:
        raise GateError("--not-preregistered is only for self-service runs; manual runs publish the plan hash first")
    if not_preregistered and published_ref is not None:
        raise GateError("pass either --published-ref or --not-preregistered")
    require_agreement(run_dir, scope, now)
    plan = build_plan(run_dir, scope, trees, engine_identity)
    digest = plan_hash(plan)
    if current.get("plan_sha256") is None:
        if published_ref is not None:
            raise GateError("run freeze once without --published-ref, publish the printed hash, then pass its URL")
        write_json(Path(run_dir) / FILE, plan)
        current["plan_sha256"] = digest
        state.save(run_dir, current)
        if not not_preregistered:
            return digest, False
    if not_preregistered:
        if digest != current["plan_sha256"] or plan_hash(read_json(Path(run_dir) / FILE)) != digest:
            raise PlanError("the plan changed after its hash was printed; start a new run")
        state.transition(run_dir, "FROZEN", now, note="frozen without preregistration (self-service)",
                         preregistered=False)
        return digest, True
    if digest != current["plan_sha256"] or plan_hash(read_json(Path(run_dir) / FILE)) != digest:
        raise PlanError("the plan changed after its hash was printed; start a new run")
    if published_ref is None:
        return digest, False
    if not published_ref.startswith("https://"):
        raise GateError("--published-ref must be an https URL")
    state.transition(run_dir, "FROZEN", now, note="plan hash published", plan_published_ref=published_ref,
                     preregistered=True)
    return digest, True
