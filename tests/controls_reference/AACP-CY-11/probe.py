"""AACP reference probe for AACP-CY-11. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    import hashlib
    good, other = b"print('pinned')", b"print('replaced')"
    pin = hashlib.sha256(good).hexdigest()
    if subject.load(pin, lambda: good) != "EXECUTED:" + pin:
        harness("the unchanged artifact does not load")
    if subject.load(pin, lambda: other) != "REJECTED":
        harness("a wrong artifact is not rejected; the loader verifies nothing, adapt the probe")
    reads = iter([good, other, other, other])
    outcome = subject.load(pin, lambda: next(reads))
    return outcome == "EXECUTED:" + hashlib.sha256(other).hexdigest()


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
