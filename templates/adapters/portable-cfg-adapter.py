"""Template adapter for `aacp adversarial`.

Copy this file into the subject implementation and replace each UNSUPPORTED
branch with a call into the implementation under test.  Do not read expected
answers from AACP; the runner owns classification.
"""


def run_case(case):
    kind = case["kind"]

    if kind == "exact_call":
        # Arrange authority for challenge["authorized_call"], then present the
        # mutated/late-mutated call at the phase named by the challenge.
        # Return either:
        #   {"execution": "COMPLETED", "outcome": "REFUSED"}
        # or
        #   {"execution": "COMPLETED", "outcome": "EXECUTED",
        #    "executed_call": <the call that actually reached the effect>}
        return {"execution": "UNSUPPORTED", "message": "map exact-call hooks"}

    if kind == "freshness":
        # Authorize under authorized_context, move to dispatch_context, then
        # attempt the same protected action.
        # Return outcome REFUSED or EXECUTED.
        return {"execution": "UNSUPPORTED", "message": "map freshness hooks"}

    if kind == "effect_compare":
        # Evaluate the supplied postcondition contract over observed state.
        # For a rejected malformed contract return:
        #   {"execution": "COMPLETED", "outcome": "INVALID_INPUT"}
        # Otherwise return:
        #   {"execution": "COMPLETED", "effect_status": "EFFECT_VERIFIED"|...}
        return {"execution": "UNSUPPORTED", "message": "map effect verifier"}

    if kind == "receipt":
        # Submit the supplied receipt against the supplied server-owned lineage.
        # Return outcome ACCEPTED or REFUSED.
        return {"execution": "UNSUPPORTED", "message": "map receipt admission"}

    if kind == "receipt_sequence":
        # Submit both receipts in order and report what happened to each:
        # {"execution": "COMPLETED", "steps": [
        #   {"id": "unbound_unsupported", "outcome": "ACCEPTED"|"REFUSED"},
        #   {"id": "legitimate_verified", "outcome": "ACCEPTED"|"REFUSED"}]}
        return {"execution": "UNSUPPORTED", "message": "map receipt sequence"}

    return {"execution": "UNSUPPORTED", "message": f"unknown kind {kind}"}
