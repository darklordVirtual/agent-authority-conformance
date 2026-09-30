"""STATE.json: run lifecycle with a transition guard (RUN-PROTOCOL-v0.3 §4)."""

from pathlib import Path

from .canonical import read_json, write_json
from .errors import GateError

STATES = ("SCOPED", "FROZEN", "RUN", "PACKAGED", "SHARED_PRIVATE", "REVIEWED", "PUBLISHED", "WITHHELD")
TRANSITIONS = {
    "SCOPED": {"FROZEN"},
    "FROZEN": {"RUN"},
    "RUN": {"PACKAGED"},
    "PACKAGED": {"SHARED_PRIVATE"},
    "SHARED_PRIVATE": {"REVIEWED", "WITHHELD"},
    "REVIEWED": {"PUBLISHED", "WITHHELD"},
    "PUBLISHED": set(),
    "WITHHELD": set(),
}
FILE = "STATE.json"


def new_state(run_dir, now):
    state = {"state": "SCOPED", "history": [{"at": now, "state": "SCOPED", "note": "init"}],
             "plan_sha256": None, "plan_published_ref": None, "repository": None}
    save(run_dir, state)
    return state


def load_state(run_dir):
    path = Path(run_dir) / FILE
    if not path.is_file():
        raise GateError(f"{run_dir}: no {FILE}; run init first")
    state = read_json(path)
    if state.get("state") not in STATES:
        raise GateError(f"unknown state {state.get('state')!r}")
    return state


def save(run_dir, state):
    write_json(Path(run_dir) / FILE, state)


def require(run_dir, *allowed):
    state = load_state(run_dir)
    if state["state"] not in allowed:
        raise GateError(f"state is {state['state']}; this command needs {' or '.join(allowed)}")
    return state


def transition(run_dir, to, now, note="", **fields):
    state = load_state(run_dir)
    if to not in TRANSITIONS[state["state"]]:
        raise GateError(f"illegal transition {state['state']} -> {to}")
    state.update(fields)
    state["state"] = to
    state["history"].append({"at": now, "state": to, "note": note})
    save(run_dir, state)
    return state
