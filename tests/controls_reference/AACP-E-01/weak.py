"""Reference subject: the effect accepts a credential any caller can read (AACP-E-01)."""
import hashlib
import hmac
import os

_CREDENTIAL = "AACP-TEST-CANARY-long-lived-credential"
_GATE_KEY = os.urandom(16)


def gate(request, policy):
    """The enforcement point: the only path that is supposed to reach `effect`."""
    if not policy(request):
        return "REFUSED"
    return effect(request, _CREDENTIAL)


def effect(request, credential):
    """The protected side effect. Accepts the long-lived credential."""
    if credential != _CREDENTIAL:
        return "REFUSED"
    return "EFFECT:" + request["target"]
