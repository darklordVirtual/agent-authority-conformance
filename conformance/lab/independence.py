"""Independence per claim, and how lab labels read in federation-run-v1 and BCR terms.

A run label describes who implemented and ran the procedure. It is the ceiling for
run/reproduction independence only: a claim can be marked not independent (with
a reason), never more independent than its run. It does NOT establish observer
independence, trust-domain separation, signing-key custody, or observation
coverage. Those require property-specific evidence (for example
AACP-OBSERVED-EFFECT-VANTAGE-1).
"""

FEDERATION = {
    "SELF_RUN": "AUTHOR_RUN",
    "REPRODUCTION": "REPRODUCTION",
    "SECOND_IMPLEMENTATION": "SECOND_IMPLEMENTATION",
    "INDEPENDENT_IMPLEMENTATION": "INDEPENDENT_IMPLEMENTATION",
}
BCR = {
    "SELF_RUN": "BCR-0",
    "REPRODUCTION": "BCR-1",
    "SECOND_IMPLEMENTATION": "BCR-2",
    "INDEPENDENT_IMPLEMENTATION": "BCR-3 at most (BCR-4 needs separate host evidence)",
}


def per_claim(scope):
    """{claim or row id: {"independent": bool, "reason": str}}."""
    label = scope["independence"]
    out = {}
    for claim in scope.get("claims", []) + scope.get("rows", []):
        if claim.get("independent") is False:
            out[claim["id"]] = {"independent": False, "reason": claim["not_independent_reason"]}
        elif label == "INDEPENDENT_IMPLEMENTATION":
            out[claim["id"]] = {"independent": True, "reason": scope.get("independence_statement", "")}
        else:
            out[claim["id"]] = {"independent": False, "reason": f"run label {label}"}
    return out
