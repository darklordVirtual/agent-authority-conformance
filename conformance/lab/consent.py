"""CONSENT.json: append-only, hash-chained consent log (RUN-PROTOCOL-v0.3 §4).

Every event names who said it (a GitHub handle, compared case-insensitively)
and links where they said it. Each event carries the hash of the previous one,
and STATE.json records the count and head hash after every append, so editing,
deleting or truncating events is detected and every gate refuses to proceed.
"""

import re
from pathlib import Path

from .canonical import read_json, sha256_json, write_json
from .errors import GateError

ACTIONS = frozenset({
    "scope_agreed", "run_authorized", "admission", "factual_corrections", "survivor_classification",
    "review_ack", "publication_approved", "publication_declined", "withdrawn",
})
DECISIONS = ("ADMITTED", "NOT_ADMITTED", "UNKNOWN")
DRAFTED_BY = re.compile(r"^(human|agent:[A-Za-z0-9._-]+)$")
PUBLICATION_ACTIONS = ("publication_approved", "publication_declined", "withdrawn")
GENESIS = "0" * 64
FILE = "CONSENT.json"
STATE_FILE = "STATE.json"


def handle(name):
    """GitHub handles are case-insensitive; a leading @ is not part of the handle."""
    return name.strip().lstrip("@").lower() if isinstance(name, str) else ""


def handles(names):
    return {handle(n) for n in names}


def _head(events):
    return {"count": len(events), "sha256": sha256_json(events[-1]) if events else GENESIS}


def load(run_dir):
    path = Path(run_dir) / FILE
    events = read_json(path)["events"] if path.is_file() else []
    verify_chain(events)
    state_path = Path(run_dir) / STATE_FILE
    if state_path.is_file():
        recorded = read_json(state_path).get("consent_head")
        if recorded is not None and recorded != _head(events):
            raise GateError(f"{FILE} does not match the consent head recorded in {STATE_FILE}; "
                            "events were removed or rewritten")
    return events


def verify_chain(events):
    prev = GENESIS
    for i, event in enumerate(events):
        if event.get("prev_sha256") != prev:
            raise GateError(f"{FILE} event {i} breaks the hash chain; the log was edited")
        prev = sha256_json(event)


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _check_conditions(conditions):
    if not (isinstance(conditions, list) and conditions):
        raise GateError("conditions must be a nonempty list")
    for c in conditions:
        if not (isinstance(c, dict) and _text(c.get("text")) and isinstance(c.get("claims"), list)
                and c["claims"] and all(_text(x) for x in c["claims"])):
            raise GateError("each condition needs text and a nonempty list of claim ids")


def parse_condition(text):
    """'claim_a,claim_b=condition text' -> {"claims": [...], "text": ...}. Only the first
    '=' separates claims from text, so the text may contain '=' and ','."""
    claims, sep, body = text.partition("=")
    ids = [c.strip() for c in claims.split(",") if c.strip()]
    if not sep or not ids or not body.strip():
        raise GateError(f"condition {text!r} must look like 'claim_id[,claim_id]=text'")
    return {"claims": ids, "text": body.strip()}


def add(run_dir, who, action, ref, now, *, drafted_by="human", ai_assisted=False,
        recorded_by=None, conditions=None, **context):
    """Append one event. `who` is the person whose statement it is and `ref` links that
    statement; drafted_by and ai_assisted disclose how that text was produced and never
    change a gate."""
    if action not in ACTIONS:
        raise GateError(f"unknown consent action {action!r}")
    if not handle(who):
        raise GateError("consent needs --who (a GitHub handle)")
    if not isinstance(ref, str) or not ref.startswith("https://"):
        raise GateError("consent needs --ref: the https URL where the person said it")
    if not (isinstance(drafted_by, str) and DRAFTED_BY.match(drafted_by)):
        raise GateError("drafted_by must be 'human' or 'agent:<id>'")
    extra = {"drafted_by": drafted_by, "ai_assisted": bool(ai_assisted)}
    if recorded_by is not None:
        if not handle(recorded_by):
            raise GateError("recorded_by must be a handle")
        extra["recorded_by"] = handle(recorded_by)
    if conditions is not None:
        if action != "scope_agreed":
            raise GateError("conditions can only be attached to scope_agreed")
        _check_conditions(conditions)
        extra["conditions"] = conditions
    if action == "admission":
        if not (_text(context.get("input")) and context.get("decision") in DECISIONS
                and _text(context.get("rationale"))):
            raise GateError(f"admission needs input, decision ({', '.join(DECISIONS)}) and rationale")
    events = load(run_dir)
    prev = sha256_json(events[-1]) if events else GENESIS
    event = {"at": now, "who": handle(who), "action": action, "ref": ref, "prev_sha256": prev,
             **extra, **context}
    events.append(event)
    write_json(Path(run_dir) / FILE, {"events": events})
    state_path = Path(run_dir) / STATE_FILE
    if state_path.is_file():
        state = read_json(state_path)
        state["consent_head"] = _head(events)
        write_json(state_path, state)
    return event


def admissions(events):
    """Latest admission event per input id, with its index in the log."""
    out = {}
    for i, event in enumerate(events):
        if event["action"] == "admission":
            out[event["input"]] = {**event, "index": i}
    return out


def conditions(events):
    """Every condition attached to a scope confirmation, in log order."""
    return [{"who": e["who"], "text": c["text"], "claims": c["claims"]}
            for e in events if e["action"] == "scope_agreed" for c in e.get("conditions", [])]


def has_all(events, people, action):
    return handles(people) <= {handle(e["who"]) for e in events if e["action"] == action}


def publication_status(events, approvers, since=0):
    """approved only when every approver approved after event index `since` (the
    delivery) and after the latest factual correction; any decline or withdrawal
    by an approver at any time after `since` blocks."""
    wanted = handles(approvers)
    latest = {}
    for event in events[since:]:
        who = handle(event["who"])
        if event["action"] == "factual_corrections":
            latest = {w: a for w, a in latest.items() if a != "publication_approved"}
        elif event["action"] in PUBLICATION_ACTIONS and who in wanted:
            latest[who] = event["action"]
    if any(action != "publication_approved" for action in latest.values()):
        return "declined"
    if wanted <= set(latest):
        return "approved"
    return "pending"
