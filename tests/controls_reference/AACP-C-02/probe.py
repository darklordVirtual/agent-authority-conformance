"""AACP reference probe for AACP-C-02. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

The subject under test is `subject.py` in the working directory. A legitimate
workflow is exercised first; if it is broken the probe reports a harness error
rather than a protection that held.
"""
import sys

sys.path.insert(0, ".")
try:
    import subject
except Exception as exc:  # noqa: BLE001
    print("harness: cannot import subject:", exc)
    sys.exit(3)


def harness(msg):
    print("harness:", msg)
    sys.exit(3)


def main():
    call = {"call_id": "c-1", "tool": "pay", "args": {"to": "alice", "amount": 1}}
    subject.approve(call)
    if subject.dispatch(dict(call)) != "EXECUTED":
        harness("the approved call itself does not execute")
    substituted = {"call_id": "c-1", "tool": "pay", "args": {"to": "mallory", "amount": 1000000}}
    outcome = subject.dispatch(substituted)
    return outcome == "EXECUTED" and substituted in subject.EXECUTED


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
