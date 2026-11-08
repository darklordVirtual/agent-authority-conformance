"""Reference subject: the loader verifies one read and executes another (AACP-CY-11)."""
import hashlib


def load(pinned_digest, read):
    """`read()` returns the artifact bytes from its (possibly mutable) reference."""
    if hashlib.sha256(read()).hexdigest() != pinned_digest:
        return "REJECTED"
    return execute(read())


def execute(data):
    return "EXECUTED:" + hashlib.sha256(data).hexdigest()
