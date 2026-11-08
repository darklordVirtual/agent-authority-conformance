"""AACP reference probe for AACP-G-01. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    class Honest:
        def __init__(self):
            self.state = {}

        def post(self, body):
            self.state[body["payee"]] = body["amount"]
            return 200

        def read_back(self, payee):
            return self.state.get(payee, 0)

    class AcksWithoutApplying(Honest):
        def post(self, body):
            return 200

    if subject.transfer(Honest(), "alice", 10)["outcome"] != "verified":
        harness("an applied transfer is not reported verified")
    return subject.transfer(AcksWithoutApplying(), "alice", 10)["outcome"] == "verified"


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
