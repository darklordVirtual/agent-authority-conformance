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
    plan.require_agreement(run_dir, load_scope(run_dir))  # consent gate before any fetch
    scope = load_scope(run_dir, require_pins=True)
    with tempfile.TemporaryDirectory(prefix="aac-freeze-", dir=workdir) as tmp:
        trees, _ = pins.materialize(scope, tmp)
        return plan.freeze(run_dir, scope, trees, identity_for(scope), now, published_ref)


def package(run_dir, now):
    from . import package as package_module
    package_module.build(run_dir, now)


LIFECYCLE_FILES = ("STATUS.md", "CONSENT.json", "REVIEW.md", "STATE.json")


def share(run_dir, org, invite, now):
    """Create <org>/<run_id> as a private repository, push the package, invite read-only."""
    from . import github
    state.require(run_dir, "PACKAGED")
    if not org:
        raise GateError("no organisation: set org in lab.toml or pass --org")
    if github.owner_type(org) != "Organization":
        raise GateError(f"{org} is not an organisation; user-owned repositories cannot grant read-only access")
    from .package import scan_for_leaks
    from .rerun import verify_manifest
    scope = load_scope(run_dir)
    problems = verify_manifest(Path(run_dir))
    if problems:
        raise GateError("package does not match MANIFEST.json: " + "; ".join(problems))
    scan_for_leaks(run_dir)
    full_name = f"{org}/{scope['run_id']}"
    github.create_private(full_name)
    commit = github.push_snapshot(run_dir, full_name, f"Private delivery of {scope['run_id']}")
    for user in invite:
        github.invite_read_only(full_name, user)
    state.transition(run_dir, "SHARED_PRIVATE", now, note=f"pushed {commit}; invited {', '.join(invite) or 'nobody'}",
                     repository=full_name, delivery_commit=commit,
                     consent_index_at_share=len(consent.load(run_dir)))
    return full_name


def review(run_dir, who, kind, ref, now):
    """Record corrections or survivor classification. Measured values are never edited."""
    current = state.require(run_dir, "SHARED_PRIVATE", "REVIEWED")
    scope = load_scope(run_dir)
    reviewers = consent.handles(scope["publication"]["approvers"] + scope["agreement_parties"]
                                + [m for s in scope["subjects"] for m in s["maintainers"]])
    if consent.handle(who) not in reviewers:
        raise GateError(f"{who} is not an approver, agreement party or subject maintainer of this run")
    action = {"corrections": "factual_corrections", "classification": "survivor_classification"}[kind]
    consent.add(run_dir, who, action, ref, now)
    path = Path(run_dir) / "REVIEW.md"
    if not path.is_file():
        path.write_text("# Review addenda\n\nMeasured values are never edited. Corrections and survivor "
                        "classifications are recorded here and linked to where they were made.\n\n",
                        encoding="utf-8")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"- {now}: {action} by {who}: {ref}\n")
    if current["state"] == "SHARED_PRIVATE":
        state.transition(run_dir, "REVIEWED", now, note=action)


def _set_status(run_dir, status, message):
    """Write STATUS.md and push lifecycle files; restore STATUS.md if pushing fails."""
    from . import github
    from .report import render_status
    current = state.load_state(run_dir)
    path = Path(run_dir) / "STATUS.md"
    previous = path.read_text(encoding="utf-8") if path.is_file() else None
    path.write_text(render_status(status), encoding="utf-8")
    try:
        if current.get("repository"):
            github.push_snapshot(run_dir, current["repository"], message,
                                 files=[f for f in LIFECYCLE_FILES if (Path(run_dir) / f).is_file()])
    except Exception:
        if previous is not None:
            path.write_text(previous, encoding="utf-8")
        raise
    return current


def publish(run_dir, now):
    from . import github
    current = state.require(run_dir, "REVIEWED")
    scope = load_scope(run_dir)
    approvers = scope["publication"]["approvers"]
    status = consent.publication_status(consent.load(run_dir), approvers, since=current["consent_index_at_share"])
    if status != "approved":
        raise GateError(f"publication is {status}; every approver ({', '.join(approvers)}) must approve "
                        "after delivery and after the latest factual correction")
    current = _set_status(run_dir, "PUBLISHED", "Record publication approval")
    github.make_public(current["repository"])
    state.transition(run_dir, "PUBLISHED", now, note="every approver approved publication")


def withhold(run_dir, now):
    current = state.require(run_dir, "SHARED_PRIVATE", "REVIEWED")
    scope = load_scope(run_dir)
    if consent.publication_status(consent.load(run_dir), scope["publication"]["approvers"],
                                  since=current["consent_index_at_share"]) != "declined":
        raise GateError("withhold needs a publication_declined or withdrawn event from an approver")
    _set_status(run_dir, "WITHHELD", "Record withheld status")
    state.transition(run_dir, "WITHHELD", now, note="publication declined")
