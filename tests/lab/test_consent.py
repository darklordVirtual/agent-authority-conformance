import json
import unittest

from conformance.lab import consent
from conformance.lab.errors import GateError
from tests.lab.helpers import AGREE_REF, NOW, LabTest


class ConsentTest(LabTest):
    def test_add_requires_https_ref_and_known_action(self):
        with self.assertRaises(GateError):
            consent.add(self.tmp, "a", "scope_agreed", "http://x", NOW)
        with self.assertRaises(GateError):
            consent.add(self.tmp, "a", "approved", AGREE_REF, NOW)
        with self.assertRaises(GateError):
            consent.add(self.tmp, "", "scope_agreed", AGREE_REF, NOW)

    def test_chain_detects_edits(self):
        consent.add(self.tmp, "a", "scope_agreed", AGREE_REF, NOW)
        consent.add(self.tmp, "b", "scope_agreed", AGREE_REF, NOW)
        path = self.tmp / consent.FILE
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["events"][0]["who"] = "mallory"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(GateError, "hash chain"):
            consent.load(self.tmp)

    def test_deleting_an_event_breaks_the_chain(self):
        for who in ("a", "b", "c"):
            consent.add(self.tmp, who, "scope_agreed", AGREE_REF, NOW)
        path = self.tmp / consent.FILE
        doc = json.loads(path.read_text(encoding="utf-8"))
        del doc["events"][1]
        path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(GateError):
            consent.load(self.tmp)

    def test_has_all(self):
        consent.add(self.tmp, "a", "scope_agreed", AGREE_REF, NOW)
        events = consent.load(self.tmp)
        self.assertTrue(consent.has_all(events, ["a"], "scope_agreed"))
        self.assertFalse(consent.has_all(events, ["a", "b"], "scope_agreed"))

    def test_publication_status(self):
        approvers = ["a", "b"]
        self.assertEqual(consent.publication_status([], approvers), "pending")
        consent.add(self.tmp, "a", "publication_approved", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), approvers), "pending")
        consent.add(self.tmp, "b", "publication_approved", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), approvers), "approved")
        consent.add(self.tmp, "b", "withdrawn", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), approvers), "declined")

    def test_decline_blocks_even_if_others_approved(self):
        consent.add(self.tmp, "a", "publication_approved", AGREE_REF, NOW)
        consent.add(self.tmp, "b", "publication_declined", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), ["a", "b"]), "declined")

    def test_non_approver_approval_ignored(self):
        consent.add(self.tmp, "a", "publication_approved", AGREE_REF, NOW)
        consent.add(self.tmp, "bystander", "publication_approved", AGREE_REF, NOW)
        self.assertEqual(consent.publication_status(consent.load(self.tmp), ["a", "b"]), "pending")


if __name__ == "__main__":
    unittest.main()
