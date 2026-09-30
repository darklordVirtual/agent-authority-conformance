import json
import tempfile
import unittest
from pathlib import Path
from conformance.adapter import AdapterError, resolve, sha256_bytes, validate_manifest

class AdapterTests(unittest.TestCase):
    def manifest(self, content=b"evidence\n"):
        return {
            "schema_version":"federation-adapter-v1",
            "subject":{"repository":"example/project","revision":"a"*40},
            "adapter":{"id":"example-v1","revision":"b"*40},
            "artifacts":[{"id":"e1","path":"evidence.txt","sha256":sha256_bytes(content),"source_class":"test_fixture","required":True}],
            "claims":[{"claim_id":"c1","property":"C","procedure":"example-v1","artifacts":["e1"],"claim_ceiling":"Only the pinned fixture bytes were resolved."}],
            "explicit_non_claims":["production enforcement"],
            "review":{"maintainer_review_required":True}
        }

    def test_resolved_is_not_a_property_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"evidence\n")
            out=resolve(self.manifest(),d)
            self.assertEqual(out["adapter_status"],"RESOLVED")
            self.assertEqual(out["claims"][0]["evidence_resolution"],"RESOLVED")
            self.assertIsNone(out["claims"][0]["property_verdict"])
            self.assertFalse(out["publication_authorized"])
            self.assertEqual(out["review_state"],"DRAFT_PRIVATE_REVIEW")

    def test_hash_mismatch_is_invalid_input_not_fail(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"changed")
            out=resolve(self.manifest(),d)
            self.assertEqual(out["adapter_status"],"INVALID_INPUT")
            self.assertEqual(out["evidence"][0]["resolution"],"HASH_MISMATCH")
            self.assertIsNone(out["claims"][0]["property_verdict"])

    def test_missing_is_invalid_input_not_fail(self):
        with tempfile.TemporaryDirectory() as d:
            out=resolve(self.manifest(),d)
            self.assertEqual(out["evidence"][0]["resolution"],"MISSING")
            self.assertIsNone(out["claims"][0]["property_verdict"])

    def test_deterministic_output(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"evidence\n")
            self.assertEqual(resolve(self.manifest(),d),resolve(self.manifest(),d))

    def test_rejects_relative_traversal(self):
        m=self.manifest(); m["artifacts"][0]["path"]="../secret"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_absolute_artifact_path(self):
        m=self.manifest(); m["artifacts"][0]["path"]="/tmp/evidence"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_duplicate_artifact_ids(self):
        m=self.manifest(); m["artifacts"].append(dict(m["artifacts"][0]))
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_unpinned_adapter_revision(self):
        m=self.manifest(); m["adapter"]["revision"]="main"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_short_revision(self):
        m=self.manifest(); m["subject"]["revision"]="main"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_verdict_in_adapter_claim(self):
        m=self.manifest(); m["claims"][0]["status"]="PASS"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_unknown_artifact_reference(self):
        m=self.manifest(); m["claims"][0]["artifacts"]=["missing"]
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_requires_maintainer_review_gate(self):
        m=self.manifest(); m["review"]["maintainer_review_required"]=False
        with self.assertRaises(AdapterError): validate_manifest(m)

if __name__=="__main__":
    unittest.main()
