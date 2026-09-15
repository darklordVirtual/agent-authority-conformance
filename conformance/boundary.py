"""Bounded E inference over evidence already accepted by an assessor.

This does not authenticate artifacts, inspect credentials, discover paths, or
establish observation coverage. Those are upstream evidence-admission duties.
No runtime action is performed, and no expected answer is accepted as input.
"""

from jsonschema import ValidationError

from .validation import load_validator

MINIMUM_CLASSES = frozenset({
    "without_authorization", "unregistered_tool", "extracted_callable",
    "shared_process_credential", "authenticated_client",
})
INPUT_VALIDATOR = load_validator("execution-boundary-input-v0.2.schema.json")


class InvalidInput(ValueError):
    """The applicable inference has not run because input is malformed."""


class UnsupportedVerification(ValueError):
    """No applicable procedure exists in this bounded reference checker."""


def evaluate(document):
    """Return a scoped property verdict; errors are distinct non-verdicts."""
    try:
        INPUT_VALIDATOR.validate(document)
    except ValidationError as exc:
        raise InvalidInput(exc.message) from exc
    if document["property"] != "E":
        raise UnsupportedVerification(document["property"])

    context = document["context"]
    scope = context["evaluation_scope"]
    attempts = [a for a in document["attempts"] if a["scope"] == scope]

    def result(status, obligations):
        return {"property": "E", "evaluation_scope": scope,
                "status": status, "unresolved_obligations": obligations}

    # A positively observed bypass does not require complete observation.
    if any(a["outcome"] == "REACHED_EFFECT" for a in attempts):
        return result("FAIL", [])

    missing = []
    for key, obligation in (("accepted_topology", "credential_topology"),
                            ("accepted_coverage", "observation_coverage")):
        premise = context[key]
        if premise is None or premise["scope"] != scope:
            missing.append(obligation)
    attempted = {a["class"] for a in attempts}
    if not MINIMUM_CLASSES <= attempted:
        missing.append("minimum_bypass_classes")
    if any(a["outcome"] == "UNKNOWN" for a in attempts):
        missing.append("attempt_outcomes")
    if missing:
        return result("NOT_ESTABLISHED", missing)
    return result("PASS", [])
