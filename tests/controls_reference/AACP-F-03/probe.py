"""AACP reference probe for AACP-F-03. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    if subject.approve("c-1", expires_at=10, now=0) != "APPROVED":
        harness("a fresh approval is refused")
    if subject.dispatch("c-1", now=5) != "EXECUTED":
        harness("dispatch within the lifetime does not execute")
    if subject.approve("late", expires_at=10, now=20) != "REFUSED":
        harness("approval does not check expiry at all; adapt the probe")
    return subject.dispatch("c-1", now=11) == "EXECUTED"


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
