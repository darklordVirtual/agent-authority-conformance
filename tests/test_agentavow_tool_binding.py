import json
import hashlib
from pathlib import Path
import unittest

from conformance.agentavow_tool_binding import evaluate, tool_digest, tool_key
from conformance.validation import load_validator

FIXTURE_PATH = Path(__file__).parents[1] / "interop" / "fixtures" / "agentavow-tool-manifest-digest-v1.json"
MANIFEST_PATH = Path(__file__).parents[1] / "interop" / "fixtures" / "agentavow-tool-manifest-digest-v1.manifest.json"


def fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class AgentAvowToolBindingTests(unittest.TestCase):
    def test_producer_package_manifest_pins_fixture_bytes(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        load_validator("federation-producer-package-v1.schema.json").validate(manifest)
        self.assertEqual(manifest["schema_version"], "federation-producer-package-v1")
        self.assertEqual(manifest["producer_revision"], "36426cfd5152bba6a27766febfac8aaef47b6f34")
        self.assertIn("does not establish runtime behavior", manifest["claim_ceiling"])
        for entry in manifest["package_files"]:
            path = MANIFEST_PATH.parents[2] / entry["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], entry["path"])

    def test_tampered_producer_artifact_fails_package_pin(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        entry = manifest["package_files"][0]
        digest = hashlib.sha256((FIXTURE_PATH.read_bytes() + b"\n")).hexdigest()
        self.assertNotEqual(digest, entry["sha256"])

    def test_key_encoding_vectors(self):
        data = fixture()
        self.assertEqual(len(data["key_encoding"]), 13)
        for vector in data["key_encoding"]:
            with self.subTest(name=vector["name"]):
                self.assertEqual(tool_key(vector["name"]), vector["key"])

    def test_observed_tool_digests_recompute(self):
        data = fixture()
        expected = data["attestation"]["toolDigests"]
        self.assertEqual(len(data["observed_tools"]), 3)
        for tool in data["observed_tools"]:
            with self.subTest(tool=tool["name"]):
                self.assertEqual(tool_digest(tool), expected[tool_key(tool["name"])])

    def test_gate_vectors(self):
        data = fixture()
        self.assertEqual(len(data["vectors"]), 6)
        for vector in data["vectors"]:
            with self.subTest(vector=vector["name"]):
                self.assertEqual(evaluate(vector, data), vector["expect"])

    def test_claim_ceiling_is_not_runtime_authority_or_effect(self):
        ceiling = fixture()["claim_ceiling"].lower()
        self.assertIn("nothing about runtime behavior", ceiling)
        self.assertIn("whether a gate proceeds", ceiling)


if __name__ == "__main__":
    unittest.main()
