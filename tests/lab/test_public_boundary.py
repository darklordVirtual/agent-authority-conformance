"""Public-boundary self-service compatibility: #177 direction without producer impersonation."""

import json
import unittest

from conformance.lab.errors import ScopeError
from conformance.lab.scope import validate_scope
from tests.lab.helpers import FIXTURES


BOUNDARY = {
    "repo": "https://github.com/example/producer",
    "commit": "0123456789abcdef0123456789abcdef01234567",
    "path": "CLAIM-BOUNDARY.md",
    "sha256": "a" * 64,
    "procedure_ref": "INVITATION.md",
    "claims_ref": "CLAIM-BOUNDARY.md#claims",
    "classification_ref": "CLAIM-BOUNDARY.md#classification",
}


class PublicBoundaryScopeTest(unittest.TestCase):
    def scope(self):
        scope = json.loads((FIXTURES / "toy-offer-run" / "SCOPE.json").read_text(encoding="utf-8"))
        scope.pop("offer")
        scope["public_boundary"] = dict(BOUNDARY)
        return scope

    def test_public_boundary_is_valid_self_service_basis(self):
        validate_scope(self.scope())

    def test_public_boundary_does_not_require_producer_offer(self):
        scope = self.scope()
        self.assertNotIn("offer", scope)
        validate_scope(scope)

    def test_offer_and_public_boundary_are_mutually_exclusive(self):
        scope = self.scope()
        scope["offer"] = {
            "repo": BOUNDARY["repo"], "commit": BOUNDARY["commit"], "path": "aacp-offers.json",
            "offer_id": "x", "sha256": "b" * 64,
        }
        with self.assertRaisesRegex(ScopeError, "exactly one basis"):
            validate_scope(scope)

    def test_public_boundary_requires_classification_rules(self):
        scope = self.scope()
        scope["public_boundary"].pop("classification_ref")
        with self.assertRaisesRegex(ScopeError, "classification_ref"):
            validate_scope(scope)


if __name__ == "__main__":
    unittest.main()
