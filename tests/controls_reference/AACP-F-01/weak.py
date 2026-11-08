"""Reference subject: dispatch checks that an approval exists, not what it approved (AACP-F-01)."""
import json

RECORDS = {"inv-1": {"payee": "alice", "amount": 10}}
APPROVALS = {}


def snapshot(record):
    return json.dumps(record, sort_keys=True)


def approve(record_id):
    APPROVALS[record_id] = snapshot(RECORDS[record_id])
    return "APPROVED"


def dispatch(record_id):
    if record_id not in APPROVALS:
        return "REFUSED"
    return "EXECUTED:" + snapshot(RECORDS[record_id])
