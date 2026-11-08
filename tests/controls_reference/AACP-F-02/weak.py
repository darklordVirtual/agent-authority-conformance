"""Reference subject: check-then-consume of a single-use token is not atomic (AACP-F-02)."""
import threading
import time

USED = set()
_LOCK = threading.Lock()


def consume(token):
    if token in USED:
        return "REFUSED"
    time.sleep(0.02)  # models the round trip to the use-state store
    USED.add(token)
    return "EXECUTED"
