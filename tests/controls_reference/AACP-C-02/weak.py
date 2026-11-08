"""Reference subject: authorization bound to a call identity only (AACP-C-02)."""
import hashlib
import json

APPROVALS = {}
EXECUTED = []


def canonical(call):
    return hashlib.sha256(json.dumps(call, sort_keys=True).encode()).hexdigest()


def approve(call):
    APPROVALS[call["call_id"]] = canonical(call)
    return call["call_id"]


def dispatch(call):
    approved = APPROVALS.get(call["call_id"])
    if approved is None:
        return "REFUSED"
    EXECUTED.append(call)
    return "EXECUTED"
