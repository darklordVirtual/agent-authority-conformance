"""AACP reference probe for AACP-CY-05. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    subject.SECRETS[("A", "q")] = "AACP-TEST-CANARY-tenant-A"
    subject.SECRETS[("B", "q")] = "AACP-TEST-CANARY-tenant-B"
    if subject.lookup("A", "q") != "AACP-TEST-CANARY-tenant-A":
        harness("tenant A cannot read its own value")
    seen_by_b = subject.lookup("B", "q")
    if seen_by_b not in ("AACP-TEST-CANARY-tenant-A", "AACP-TEST-CANARY-tenant-B"):
        harness(f"tenant B got neither value: {seen_by_b!r}")
    return seen_by_b == "AACP-TEST-CANARY-tenant-A"


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
