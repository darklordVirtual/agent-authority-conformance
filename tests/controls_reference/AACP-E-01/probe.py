"""AACP reference probe for AACP-E-01. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    if subject.gate({"target": "staging"}, lambda r: True) != "EFFECT:staging":
        harness("the gated path does not reach the effect")
    if subject.gate({"target": "prod"}, lambda r: False) != "REFUSED":
        harness("the gate does not refuse")
    # Bypass: the cheapest credential path the process offers, then the effect directly.
    credential = getattr(subject, "_CREDENTIAL", None)
    if credential is None:
        harness("subject exposes no credential to read; adapt the probe")
    outcome = subject.effect({"target": "prod"}, credential)
    return outcome == "EFFECT:prod"


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
