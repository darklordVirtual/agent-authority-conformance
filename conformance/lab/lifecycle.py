"""Lifecycle commands other than run (RUN-PROTOCOL-v0.3 §4)."""

import shutil
import tempfile
from pathlib import Path

from . import LAB_VERSION, consent, pins, plan, state
from .canonical import read_json, write_json
from .engines.base import identity_for
from .errors import GateError
from .scope import load_scope, validate_scope


def skeleton(run_id, kind):
    scope = {
        "lab_version": LAB_VERSION, "run_id": run_id, "kind": kind, "agreement_ref": None,
        "independence": "SELF_RUN",
        "runner": {"project": "Agent Authority Conformance", "maintainers": []},
        "agreement_parties": [],
        "subjects": [{"project": "", "maintainers": [], "repo": "", "commit": "", "paths": [],
                      "files_sha256": {}, "license": "", "attribution": ""}],
        "claim_ceiling": {"establishes": [], "does_not_establish": []},
        "publication": {"private_first": True, "approvers": [], "unreleased_citable": False},
    }
    if kind == "adequacy":
        scope.update(rows=[], controls={"positive": "controls/positive.json", "inert": "controls/inert.json"},
                     engine={"name": "native", "cross_check": None})
    else:
        scope.update(inputs=[], claims=[], reference_time=None)
    return scope


def init(runs_dir, run_id, kind, now, template=None, follow_up=None, commit=None):
    runs_dir = Path(runs_dir)
    run_dir = runs_dir / run_id
    if run_dir.exists():
        raise GateError(f"{run_dir} already exists")
    if follow_up:
        if not commit:
            raise GateError("--follow-up needs --commit")
        previous = runs_dir / follow_up
        prev_scope, prev_state = read_json(previous / "SCOPE.json"), state.load_state(previous)
        if len(prev_scope["subjects"]) != 1:
            raise GateError("--follow-up supports single-subject runs")
        if not prev_state.get("plan_sha256"):
            raise GateError(f"{follow_up} has no frozen plan to follow up")
        run_dir.mkdir(parents=True)
        for sub in plan.RUN_OWNED:
            if (previous / sub).is_dir():
                shutil.copytree(previous / sub, run_dir / sub)
        for name in plan.RUN_OWNED_FILES:
            if (previous / name).is_file():
                shutil.copy2(previous / name, run_dir / name)
        scope = {**prev_scope, "run_id": run_id,
                 "previous_run": {"run_id": follow_up, "plan_sha256": prev_state["plan_sha256"]},
                 "subjects": [{**prev_scope["subjects"][0], "commit": commit, "files_sha256": {}}]}
    elif template:
        scope = read_json(template)
        scope["run_id"] = run_id
        run_dir.mkdir(parents=True)
    else:
        if kind not in ("adequacy", "verification"):
            raise GateError("init needs --kind adequacy or --kind verification")
        scope = skeleton(run_id, kind)
        run_dir.mkdir(parents=True)
    if kind and scope["kind"] != kind:
        shutil.rmtree(run_dir)
        raise GateError(f"template kind {scope['kind']} does not match --kind {kind}")
    write_json(run_dir / "SCOPE.json", scope)
    write_json(run_dir / consent.FILE, {"events": []})
    state.new_state(run_dir, now)
    return run_dir


def pin(run_dir, workdir=None):
    """Fill files_sha256 from the pinned commits. Refused once anyone agreed the scope."""
    state.require(run_dir, "SCOPED")
    if any(e["action"] == "scope_agreed" for e in consent.load(run_dir)):
        raise GateError("pins cannot change after scope_agreed; start a new run")
    path = Path(run_dir) / "SCOPE.json"
    scope = read_json(path)
    validate_scope(scope)
    with tempfile.TemporaryDirectory(prefix="aac-pin-", dir=workdir) as tmp:
        for i, subject in enumerate(scope["subjects"]):
            clone = pins.fetch(subject["repo"], subject["commit"], Path(tmp) / f"clone-{i}")
            subject["files_sha256"] = pins.hash_paths(clone, subject["paths"])
    validate_scope(scope, require_pins=True)
    write_json(path, scope)
    return scope


def freeze(run_dir, now, published_ref=None, workdir=None):
    state.require(run_dir, "SCOPED")
    scope = load_scope(run_dir, require_pins=True)
    plan.require_agreement(run_dir, scope)
    with tempfile.TemporaryDirectory(prefix="aac-freeze-", dir=workdir) as tmp:
        trees, _ = pins.materialize(scope, tmp)
        return plan.freeze(run_dir, scope, trees, identity_for(scope), now, published_ref)


def package(run_dir, now):
    from . import package as package_module
    package_module.build(run_dir, now)
