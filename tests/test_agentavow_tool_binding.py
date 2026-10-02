import json
from pathlib import Path

from conformance.agentavow_tool_binding import evaluate, tool_digest, tool_key

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "agentavow-tool-manifest-digest-v1.json"


def fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_agentavow_key_encoding_vectors():
    data = fixture()
    assert len(data["key_encoding"]) == 13
    for vector in data["key_encoding"]:
        assert tool_key(vector["name"]) == vector["key"]


def test_agentavow_observed_tool_digests_recompute():
    data = fixture()
    expected = data["attestation"]["toolDigests"]
    assert len(data["observed_tools"]) == 3
    for tool in data["observed_tools"]:
        assert tool_digest(tool) == expected[tool_key(tool["name"])]


def test_agentavow_gate_vectors():
    data = fixture()
    assert len(data["vectors"]) == 6
    for vector in data["vectors"]:
        assert evaluate(vector, data) == vector["expect"]


def test_claim_ceiling_is_not_runtime_authority_or_effect():
    data = fixture()
    ceiling = data["claim_ceiling"].lower()
    assert "nothing about runtime behavior" in ceiling
    assert "whether a gate proceeds" in ceiling
