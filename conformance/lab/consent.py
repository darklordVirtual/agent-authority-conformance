"""CONSENT.json: append-only, hash-chained consent log (RUN-PROTOCOL-v0.3 §5).

Every event names who said it and links where they said it. The tool never
rewrites events; any edit breaks the chain and every gate refuses to proceed.
"""

from pathlib import Path

from .canonical import read_json, sha256_json, write_json
from .errors import GateError

ACTIONS = frozenset({
    "scope_agreed", "run_authorized", "factual_corrections", "survivor_classification",
    "publication_approved", "publication_declined", "withdrawn",
})
PUBLICATION_ACTIONS = ("publication_approved", "publication_declined", "withdrawn")
GENESIS = "0" * 64
FILE = "CONSENT.json"


def load(run_dir):
    path = Path(run_dir) / FILE
    events = read_json(path)["events"] if path.is_file() else []
    verify_chain(events)
    return events


def verify_chain(events):
    prev = GENESIS
    for i, event in enumerate(events):
        if event.get("prev_sha256") != prev:
            raise GateError(f"{FILE} event {i} breaks the hash chain; the log was edited")
        prev = sha256_json(event)


def add(run_dir, who, action, ref, now):
    if action not in ACTIONS:
        raise GateError(f"unknown consent action {action!r}")
    if not isinstance(who, str) or not who.strip():
        raise GateError("consent needs --who (a GitHub handle)")
    if not isinstance(ref, str) or not ref.startswith("https://"):
        raise GateError("consent needs --ref: the https URL where the person said it")
    events = load(run_dir)
    prev = sha256_json(events[-1]) if events else GENESIS
    event = {"at": now, "who": who, "action": action, "ref": ref, "prev_sha256": prev}
    events.append(event)
    write_json(Path(run_dir) / FILE, {"events": events})
    return event


def has_all(events, people, action):
    given = {e["who"] for e in events if e["action"] == action}
    return set(people) <= given


def publication_status(events, approvers):
    """approved only when every approver's latest publication event approves."""
    latest = {}
    for event in events:
        if event["action"] in PUBLICATION_ACTIONS and event["who"] in approvers:
            latest[event["who"]] = event["action"]
    if any(action != "publication_approved" for action in latest.values()):
        return "declined"
    if set(approvers) <= set(latest):
        return "approved"
    return "pending"
