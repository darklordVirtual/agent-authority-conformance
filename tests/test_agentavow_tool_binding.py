import json
from pathlib import Path
import unittest

from conformance.agentavow_tool_binding import evaluate, tool_digest, tool_key

FIXTURE_PATH = Path(__file__).parents[1] / "interop" / "fixtures" / "agentavow-tool-manifest-digest-v1.json"


def fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class AgentAvowToolBindingTests(unittest.TestCase):
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
