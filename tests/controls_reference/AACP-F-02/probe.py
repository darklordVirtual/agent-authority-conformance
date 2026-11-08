"""AACP reference probe for AACP-F-02. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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
    import threading
    if subject.consume("seq") != "EXECUTED" or subject.consume("seq") != "REFUSED":
        harness("sequential reuse is not refused; this is not a race (see AACP-A-01)")
    n = 8
    barrier = threading.Barrier(n)
    outcomes = []

    def worker():
        barrier.wait()
        outcomes.append(subject.consume("race"))

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    executed = outcomes.count("EXECUTED")
    if executed == 0:
        harness("no concurrent presentation executed at all")
    return executed > 1


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
