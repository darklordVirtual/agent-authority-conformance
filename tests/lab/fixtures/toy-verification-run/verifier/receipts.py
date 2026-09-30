"""Toy verifier used by the lab tests: our own checks, no producer code."""


def cap_compliance(doc, context):
    ok = doc["execution"]["nativeValue"] <= doc["delegation"]["cap"]
    return {"result": "ESTABLISHED" if ok else "CONTRADICTED",
            "reads": ["execution.nativeValue", "delegation.cap"]}


def exact_call(doc, context):
    ok = doc["execution"]["nativeValue"] == doc["authorization"]["value"]
    return {"result": "ESTABLISHED" if ok else "CONTRADICTED",
            "reads": ["execution.nativeValue", "authorization.value"]}


def signature(doc, context):
    return {"result": "NOT_ESTABLISHED", "reads": [], "unresolved_obligations": ["signature_key_pin"]}
