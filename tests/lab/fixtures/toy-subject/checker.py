"""Toy checker used only by the lab tests."""


def decide(case):
    if not case.get("signed"):
        return {"status": "rejected", "reason": "unsigned"}
    if case.get("amount", 0) > case.get("cap", 0):
        return {"status": "rejected", "reason": "over_cap"}
    if case.get("expired"):
        return {"status": "rejected", "reason": "expired"}
    return {"status": "accepted", "reason": "ok"}
