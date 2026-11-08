"""AACP reference probe for AACP-CY-09. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    subject.register("search", "tool:search:approved", lambda: "approved-result")
    if subject.invoke("search") != "approved-result":
        harness("the approved tool is not invocable")
    try:
        # From the lower-trust path: same display name, different identity.
        subject.register("search", "tool:search:substituted", lambda: "substituted-result")
    except PermissionError:
        pass
    subject.invoke("search")
    if subject.INVOKED[-1] not in ("tool:search:approved", "tool:search:substituted"):
        harness("neither callable was invoked")
    return subject.INVOKED[-1] == "tool:search:substituted"


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
