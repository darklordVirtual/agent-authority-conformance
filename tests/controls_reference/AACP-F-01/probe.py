"""AACP reference probe for AACP-F-01. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    subject.approve("inv-1")
    if not subject.dispatch("inv-1").startswith("EXECUTED"):
        harness("an unchanged approved record does not dispatch")
    subject.RECORDS["inv-1"]["amount"] = 1000000
    outcome = subject.dispatch("inv-1")
    return outcome.startswith("EXECUTED") and "1000000" in outcome


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
