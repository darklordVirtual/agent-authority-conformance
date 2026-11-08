"""Reference subject: expiry evaluated when approving, never when dispatching (AACP-F-03)."""
APPROVALS = {}


def approve(call_id, expires_at, now):
    if now >= expires_at:
        return "REFUSED"
    APPROVALS[call_id] = expires_at
    return "APPROVED"


def dispatch(call_id, now):
    if call_id not in APPROVALS:
        return "REFUSED"
    return "EXECUTED"
