"""AACP control probes for darklordVirtual/REMORA-research
@ 06c2f8f038d9d24668158ce24cbd444e89fd306a (binding controls/bindings/remora-06c2f8f).

Each test ASSERTS THAT THE WEAKNESS IS PRESENT. A passing test means the
weakness was observed; a failing test means it was not. The binding pairs
every probe with either a repair (an observed weakness must disappear) or a
weakening (a protection, once removed, must make the probe observe), so a
failing test here is only evidence when its weakening makes it pass.

Run one probe: python -m pytest -q -p no:cacheprovider -o addopts= \
    aacp_probes/test_remora_probes.py::<name>
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

os.environ.setdefault("REMORA_ENV", "development")

def setup_failed(message: str):
    """A probe whose setup or positive control fails has no verdict.

    Exit code 3 is outside the binding's not_observed_exit ([1]), so the
    runner records NON_VERDICT; it is never read as a protection that held.
    """
    pytest.exit(f"AACP setup failed: {message}", returncode=3)


# A write tool with a real, sandboxed side effect (a JSON file).
def store_call(artifact_id: str) -> dict:
    return {"tool_name": "store_artifact",
            "arguments": {"artifact_id": artifact_id, "content": {"aacp": artifact_id}},
            "target_environment": "staging"}


# ---------------------------------------------------------------- fixtures

@pytest.fixture()
def api(monkeypatch, tmp_path):
    """The governed execution API as REMORA's own execute-accepted tests build it.

    Authentication is replaced by a switchable principal; probes of
    authentication itself (B-01, B-02) use `real_auth_api` instead.
    """
    monkeypatch.setenv("REMORA_PDP_SIGNING_KEY", "aacp-probe-key-" + "0" * 32)
    monkeypatch.setenv("REMORA_ENV", "development")
    monkeypatch.setenv("REMORA_TOOL_REGISTRY_MODULE", "servers.tool_registry_research")
    monkeypatch.setenv("REMORA_EXECUTION_ARTIFACT_DIR", str(tmp_path / "art"))
    monkeypatch.delenv("REMORA_SEMANTIC_BUNDLE_MODULE", raising=False)
    from fastapi.testclient import TestClient

    import servers.api as api_mod
    import servers.execution_api as exec_mod
    from remora.governance.tenant_chain import TenantAuditChain

    who = {"principal": "agent-1", "role": "operator"}
    monkeypatch.setattr(api_mod, "_authenticate", lambda request: ("acme", who["role"]))
    monkeypatch.setattr(api_mod, "_authenticated_principal", lambda request: who["principal"])
    monkeypatch.setattr(api_mod, "_require_tenant_capability", lambda role, tenant, cap: None)
    exec_mod._QUEUES.clear()
    exec_mod._ITEM_TENANT.clear()
    exec_mod._CHAIN = TenantAuditChain()
    exec_mod._GATE = exec_mod.EnforcementGate(strict=True, audience=exec_mod.PEP_AUDIENCE)
    exec_mod._reset_semantic_bundle()
    exec_mod._reset_tool_dispatcher()
    exec_mod._reset_outbox()
    return TestClient(api_mod.app), who, tmp_path / "art"


def mint(call: dict, principal: str = "agent-1", action: str = "accept") -> dict:
    """An execution token minted the way the assess ACCEPT branch mints it.

    REMORA's research profile refuses probabilistic ACCEPT without
    server-side evidence, so /assess does not reach ACCEPT here; REMORA's own
    tests mint the token directly for the same reason.
    """
    import servers.execution_api as exec_mod
    from remora.enforcement.token import PolicyDecisionToken
    from remora.execution.service import authorization_context
    from remora.policy.observation import canonical_tool_call_hash

    registry = exec_mod.TOOL_REGISTRY.get(call["tool_name"], {})
    target = str(registry.get("target_environment", call.get("target_environment", "prod")))
    call_hash = canonical_tool_call_hash(name=call["tool_name"], arguments=call["arguments"],
                                         tenant="acme", target=target)
    _obs, semantic = exec_mod._observation_with_context(exec_mod.ToolCallRequest(**call), "acme")
    now = datetime.now(UTC)
    token = PolicyDecisionToken.issue(
        action=action, observation_hash=call_hash, request_id="aacp-1",
        issued_at=now.isoformat(), expires_at=(now + timedelta(seconds=300)).isoformat(),
        audience=exec_mod.PEP_AUDIENCE,
        context=authorization_context(
            tenant="acme", principal=principal, semantic=semantic,
            target_environment=call.get("target_environment", "") or "",
            policy_bundle_hash=exec_mod._current_policy_bundle_hash(),
            toolspec_hash=str(exec_mod._resolve_toolspec(
                call["tool_name"], call["arguments"], call.get("target_environment", "") or "")["hash"])),
    )
    return token.to_dict()


def redeem(client, token: dict, call: dict):
    return client.post("/v1/execution/execute-accepted", json={"execution_token": token, "tool_call": call})


def written(art_dir, artifact_id: str) -> bool:
    return art_dir.exists() and any(artifact_id in p.name for p in art_dir.iterdir())


def control_redemption_works(client, art_dir) -> None:
    """Positive control: an honest redemption dispatches and writes. Without
    it, a refusal below could mean the path is broken, not protected."""
    call = store_call("aacp-control")
    r = redeem(client, mint(call), call)
    if r.status_code != 200 or not written(art_dir, "aacp-control"):
        setup_failed(f"positive control: honest redemption gave {r.status_code} {r.text[:200]}")


# ---------------------------------------------------------------- A

def test_a01_grant_reusable_after_restart(monkeypatch, tmp_path):
    """AACP-A-01: a one-time grant, spent and refused, is accepted again after the PEP restarts."""
    monkeypatch.setenv("REMORA_PDP_SIGNING_KEY", "aacp-probe-key-" + "0" * 32)
    from remora.enforcement.gate import EnforcementGate
    from remora.enforcement.token import PolicyDecisionToken

    now = datetime.now(UTC)
    tok = PolicyDecisionToken.issue(action="accept", observation_hash="e" * 64, request_id="a01",
                                    issued_at=now.isoformat(),
                                    expires_at=(now + timedelta(seconds=300)).isoformat(),
                                    audience="pep://aacp")
    ledger = str(tmp_path / "pep-ledger.db")
    first = EnforcementGate(strict=True, audience="pep://aacp", db_path=ledger)
    if not first.check(tok, "e" * 64, consume=True).allowed:
        setup_failed("a fresh grant was not accepted")
    if first.check(tok, "e" * 64, consume=True).allowed:
        setup_failed("the grant was not exhausted before the boundary")
    restarted = EnforcementGate(strict=True, audience="pep://aacp", db_path=ledger)
    assert restarted.check(tok, "e" * 64, consume=True).allowed, "weakness not present"


def test_a02_revocation_unknown_admits(monkeypatch):
    """AACP-A-02: when the revocation store cannot answer, admission proceeds."""
    from remora.execution.admission import AdmissionRefused, AtomicAdmission

    class Unreachable:
        def is_revoked(self, principal, *, tenant_id):
            raise RuntimeError("store down")

    admission = AtomicAdmission.__new__(AtomicAdmission)
    admission._revocations = Unreachable()
    try:
        admission._refuse_revoked("acme", ["agent-1"])
    except AdmissionRefused:
        pytest.fail("weakness not present: unknown revocation state refused")


def test_a03_grant_from_untrusted_key_accepted(monkeypatch):
    """AACP-A-03: a v3 grant signed by a key the PEP does not trust is accepted."""
    from remora.crypto import SignatureDomain, SigningKey
    from remora.enforcement.gate import EnforcementGate
    from remora.enforcement.token import PolicyDecisionToken

    pdp = SigningKey.generate({SignatureDomain.POLICY_GRANT_ASYMMETRIC})
    forger = SigningKey.generate({SignatureDomain.POLICY_GRANT_ASYMMETRIC})
    for name in ("REMORA_PDP_SIGNING_KEY", "REMORA_PDP_VERIFY_KEYS_ED25519"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("REMORA_PDP_SIGNING_KEY_ED25519_PRIVATE", forger.seed.hex())
    now = datetime.now(UTC)
    forged = PolicyDecisionToken.issue(action="accept", observation_hash="e" * 64, request_id="a03",
                                       issued_at=now.isoformat(),
                                       expires_at=(now + timedelta(seconds=120)).isoformat(),
                                       audience="pep://aacp")
    monkeypatch.delenv("REMORA_PDP_SIGNING_KEY_ED25519_PRIVATE")
    monkeypatch.setenv("REMORA_PDP_VERIFY_KEYS_ED25519", pdp.verification_key().public_bytes.hex())
    gate = EnforcementGate(strict=True, audience="pep://aacp")
    assert gate.check(forged, "e" * 64, consume=True).allowed, "weakness not present"


def test_a04_accept_token_replayable(api):
    """AACP-A-04: an ACCEPT token redeems twice on /execute-accepted."""
    client, _, art = api
    call = store_call("aacp-a04")
    token = mint(call)
    first = redeem(client, token, call)
    if first.status_code != 200:
        setup_failed(f"first redemption gave {first.status_code} {first.text[:200]}")
    second = redeem(client, token, call)
    assert second.status_code == 200, f"weakness not present: replay refused ({second.status_code})"


# ---------------------------------------------------------------- B

ASSESS = {"tool_name": "read_telemetry", "arguments": {"asset": "P-1"},
          "target_environment": "staging"}


def _real_auth_client(monkeypatch, tmp_path):
    monkeypatch.setenv("REMORA_ENV", "development")
    monkeypatch.setenv("REMORA_PDP_SIGNING_KEY", "aacp-probe-key-" + "0" * 32)
    monkeypatch.setenv("REMORA_API_TOKENS", json.dumps(
        {"tok-agent-1": {"tenant": "acme", "role": "operator", "actor_id": "agent-1"},
         "tok-admin": {"tenant": "acme", "role": "admin", "actor_id": "admin"}}))
    monkeypatch.setenv("REMORA_TOOL_REGISTRY_MODULE", "servers.tool_registry_research")
    monkeypatch.setenv("REMORA_EXECUTION_ARTIFACT_DIR", str(tmp_path / "art"))
    from fastapi.testclient import TestClient

    import servers.api as api_mod

    # The token table is read at import; reload it so this probe's table is in force.
    api_mod._TOKEN_ACTOR_IDS.clear()
    monkeypatch.setattr(api_mod, "_TOKEN_TABLE", api_mod._load_token_table())
    client = TestClient(api_mod.app)
    ok = client.post("/v1/execution/assess", json=ASSESS,
                     headers={"Authorization": "Bearer tok-agent-1"})
    if ok.status_code != 200:
        setup_failed(f"positive control: a provisioned credential gave {ok.status_code} {ok.text[:200]}")
    return client


def test_b01_unauthenticated_principal_accepted(monkeypatch, tmp_path):
    """AACP-B-01: a request naming a principal, with no credential, is served."""
    client = _real_auth_client(monkeypatch, tmp_path)
    r = client.post("/v1/execution/assess", json=ASSESS,
                    headers={"X-Remora-Tenant": "acme", "X-Remora-Actor": "admin",
                             "X-Remora-Role": "admin"})
    assert r.status_code == 200, f"weakness not present: {r.status_code}"


def test_b02_unregistered_credential_accepted(monkeypatch, tmp_path):
    """AACP-B-02: a credential the deployment never provisioned, naming a principal, is served."""
    client = _real_auth_client(monkeypatch, tmp_path)
    r = client.post("/v1/execution/assess", json=ASSESS,
                    headers={"Authorization": "Bearer tok-self-made", "X-Remora-Tenant": "acme",
                             "X-Remora-Actor": "admin"})
    assert r.status_code == 200, f"weakness not present: {r.status_code}"


def test_b03_token_redeemable_by_other_principal(api):
    """AACP-B-03: a token issued to agent-1 is redeemed by agent-2."""
    client, who, art = api
    call = store_call("aacp-b03")
    token = mint(call, principal="agent-1")
    who["principal"] = "agent-2"
    r = redeem(client, token, call)
    assert r.status_code == 200 or written(art, "aacp-b03"), f"weakness not present: {r.status_code}"


def test_b04_proposer_approves_own_call(monkeypatch):
    """AACP-B-04: in production, the principal that proposed a call approves it."""
    monkeypatch.setenv("REMORA_PDP_SIGNING_KEY", "a1" * 32)
    monkeypatch.setenv("REMORA_ENV", "development")
    monkeypatch.delenv("REMORA_REQUIRE_DISTINCT_APPROVER", raising=False)
    from fastapi.testclient import TestClient

    import servers.api as api_mod
    import servers.execution_api as exec_mod
    from remora.governance.tenant_chain import TenantAuditChain

    monkeypatch.setattr(api_mod, "_authenticate", lambda request: ("acme", "admin"))
    monkeypatch.setattr(api_mod, "_authenticated_principal", lambda request: "agent-1")
    monkeypatch.setattr(api_mod, "_is_production_mode", lambda: True)  # production's rule
    exec_mod._QUEUES.clear()
    exec_mod._ITEM_TENANT.clear()
    monkeypatch.setattr(exec_mod, "_CHAIN", TenantAuditChain())
    monkeypatch.setattr(exec_mod, "_GATE", exec_mod.EnforcementGate(strict=True, audience=exec_mod.PEP_AUDIENCE))
    exec_mod._reset_tool_dispatcher()
    client = TestClient(api_mod.app)
    body = client.post("/v1/execution/assess", json={
        "tool_name": "update_work_order", "arguments": {"order": "WO-1", "action": "reschedule"},
        "target_environment": "prod"}).json()
    if body.get("decision") != "escalate":
        setup_failed(f"expected a review item, got {body}")
    r = client.post("/v1/execution/approve",
                    json={"item_id": body["review_item_id"], "approval_ttl_seconds": 900})
    assert r.status_code == 200, f"weakness not present: {r.status_code} {r.text[:120]}"


# ---------------------------------------------------------------- C

def test_c01_token_authorizes_another_call(api):
    """AACP-C-01: a token for one call dispatches a different call (other id and content)."""
    client, _, art = api
    control_redemption_works(client, art)
    token = mint(store_call("aacp-c01-approved"))
    r = redeem(client, token, store_call("aacp-c01-substituted"))
    assert r.status_code == 200 or written(art, "aacp-c01-substituted"), \
        f"weakness not present: {r.status_code}"


# ---------------------------------------------------------------- D

LIMITS = {"schema": "remora-cumulative-limits/v1",
          "meters": {"pay": [{"quantity": "spend", "kind": "sum", "argument": "amount",
                              "unit_argument": "cur"}]},
          "limits": [{"limit_id": "spend", "tenant": "t", "quantity": "spend", "unit": "NOK",
                      "max": 100, "principal": "p"}]}


def test_d01_value_limit_bypassed(tmp_path):
    """AACP-D-01: an amount above the limit passes when encoded as another type or unit."""
    import remora.enforcement.cumulative_limits as cl

    guard = cl.LimitGuard(cl.LimitPolicy.from_dict(LIMITS), cl.LimitLedger(tmp_path / "limits.db"))
    attempts = [("1000000", "NOK"), (1000000.5, "NOK"), (-1, "NOK"), ({"v": 1000000}, "NOK"),
                (True, "NOK"), (1000000, "USD"), (1000000, "nok")]
    allowed = []
    for i, (amount, cur) in enumerate(attempts):
        refusal = guard.reserve(tenant="t", principal="p", tool_name="pay",
                                arguments={"amount": amount, "cur": cur},
                                operation_id=f"d01-{i}", request_hash=f"h-{i}", now=1_800_000_000.0)
        if refusal is None:
            allowed.append((amount, cur))
    assert allowed, "weakness not present: every encoding refused"


def test_d02_resource_restriction_escaped():
    """AACP-D-02: a resource outside workspace://reports/* satisfies the restriction."""
    from remora.capabilities.constraints import ToolConstraint, evaluate_constraint

    scope = ToolConstraint.from_dict({"conditions": [
        {"argument": "resource", "within": ["workspace://reports/*"]}]})
    escapes = ["workspace://reports/../secrets/k", "workspace://reports-x/k",
               "workspace://reports/%2e%2e/secrets", "workspace://reports\\..\\secrets",
               "workspace://reports//secrets", "workspace://reports/./../secrets",
               "workspace://other/reports/k"]
    if evaluate_constraint(scope, {"resource": "workspace://reports/q3.pdf"}) is not None:
        setup_failed("an in-scope resource was refused")
    passed = [r for r in escapes if evaluate_constraint(scope, {"resource": r}) is None]
    assert passed, "weakness not present: every escape refused"


def test_d03_effect_before_policy(api):
    """AACP-D-03: a call the PDP did not ACCEPT (ESCALATE) still takes effect at the PEP."""
    client, _, art = api
    control_redemption_works(client, art)
    call = store_call("aacp-d03")
    redeem(client, mint(call, action="escalate"), call)
    assert written(art, "aacp-d03"), "weakness not present: no effect without ACCEPT"


# ---------------------------------------------------------------- outside A-G

def _sqlite_chain(tmp_path):
    from remora.governance.tenant_chain import SQLiteTenantChain

    db = str(tmp_path / "chain.db")
    chain = SQLiteTenantChain(db)
    for i in range(3):
        chain.append("acme", {"event": "aacp", "n": i})
    return chain, db


def test_x01_sqlite_chain_tail_truncation_undetected(tmp_path):
    """AACP-X-01: deleting the newest entry of the durable SQLite chain passes verify()."""
    chain, db = _sqlite_chain(tmp_path)
    if not chain.verify("acme")[0]:
        setup_failed("an intact chain did not verify")
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM tenant_chain_entry WHERE tenant_id = 'acme' AND sequence_no = "
                     "(SELECT MAX(sequence_no) FROM tenant_chain_entry WHERE tenant_id = 'acme')")
    ok, problems = chain.verify("acme")
    assert ok and not problems, f"weakness not present: {problems}"


def test_x04_jsonl_audit_intact_log_fails_after_reload(tmp_path):
    """AACP-X-04: an untouched JSONL audit log no longer verifies once it is reloaded."""
    from remora.adapters.audit import AuditEntry
    from remora.adapters.audit.jsonl import JSONLAudit

    path = tmp_path / "audit.jsonl"
    log = JSONLAudit(str(path))
    for i in range(3):
        log.append(AuditEntry(timestamp=datetime(2026, 11, 8, 0, 0, i, tzinfo=UTC),
                              question_hash=f"q{i}", action="accept", trust_score=0.9,
                              phase="stable", oracle_count=3, verdict="ok",
                              policy_version="v1", metadata={}))
    if not log.verify():
        setup_failed("the in-process chain did not verify")
    assert not JSONLAudit(str(path)).verify(), "weakness not present: the reloaded log verifies"


def test_x02_assurance_merkle_odd_duplication():
    """AACP-X-02: remora/assurance/merkle.py gives [a,b,c] and [a,b,c,c] the same root."""
    from remora.assurance.merkle import build_merkle_tree

    assert build_merkle_tree([b"a", b"b", b"c"]).root == build_merkle_tree([b"a", b"b", b"c", b"c"]).root


def test_x02_assurance_merkle_node_as_leaf():
    """AACP-X-02: without leaf/node domain separation, an internal node verifies as a leaf."""
    from remora.assurance.merkle import MerkleProof, build_merkle_tree, verify_inclusion

    t = build_merkle_tree([b"a", b"b", b"c", b"d"])
    fake_leaf = (t.levels[0][0] + t.levels[0][1]).encode()
    proof = MerkleProof(leaf_index=0, siblings=((t.levels[1][1], "R"),))
    assert verify_inclusion(fake_leaf, proof, t.root)


def test_x02_audit_merkle_v2_odd_duplication():
    """AACP-X-02: remora/audit/merkle.py (v2, the audit default) gives [a,b,c] and [a,b,c,c] one root."""
    from remora.audit.hash_chain import AuditHashChain
    from remora.audit.merkle import compute_merkle_root

    chain = AuditHashChain()
    for i in range(3):
        chain.append(timestamp=f"2026-11-08T00:00:0{i}+00:00", question_hash=f"q{i}",
                     action="accept", trust_score=0.9, phase="stable")
    e = chain.entries()
    assert compute_merkle_root(e) == compute_merkle_root(e + [e[-1]]), "weakness not present"
