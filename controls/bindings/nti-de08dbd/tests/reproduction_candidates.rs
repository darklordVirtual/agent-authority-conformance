//! AACP control probes for abisheakp197/Neutral-Trust-Infrastructure
//! @ de08dbdcd27e01c27585d936091c69b59d173a97 (binding controls/bindings/nti-de08dbd).
//! Each test PASSES when the weakness is present. The binding's mutations check that each
//! FAILS when that weakness alone is repaired. Run via: python -m conformance.controls run
use ed25519_dalek::{Signer, SigningKey};
use ube_foundation::*;

fn req(id: &str, actor: &str, cap: &str, input: serde_json::Value) -> ActionRequest {
    ActionRequest {
        id: id.into(),
        actor: actor.into(),
        capability: cap.into(),
        action: "act".into(),
        input,
        signature: None,
        pqc_signature: None,
        public_key: None,
        pqc_public_key: None,
        token: None,
        identity_claim: None,
    }
}

fn issuer() -> (SigningKey, Vec<u8>) {
    let sk = SigningKey::from_bytes(&[7u8; 32]);
    let pk = sk.verifying_key().to_bytes().to_vec();
    (sk, pk)
}

fn token(sk: &SigningKey, id: &str, cap: &str, caveats: Vec<Caveat>) -> CapabilityToken {
    let mut t = CapabilityToken {
        id: id.into(),
        root_actor: "issuer".into(),
        capability: cap.into(),
        caveats,
        signature: vec![],
    };
    t.signature = sk.sign(&t.message_to_sign()).to_bytes().to_vec();
    t
}

fn caveat(c: CaveatType) -> Caveat {
    Caveat { location: None, condition: c }
}

/// (Critical) lib.rs:685-776 — actor is an unauthenticated string. No signature, no key
/// registry binding actor->key. Anyone naming "admin" gets admin's grants.
#[test]
fn nti_01_actor_spoofing_no_signature_required() {
    let mut e = TrustEngine::new();
    e.grant("admin", "payments");
    let d = e.evaluate(&req("r1", "admin", "payments", serde_json::json!({})));
    assert_eq!(d.decision, Decision::Allow, "spoofed actor allowed without any signature");
}

/// (Critical) lib.rs:685-710 — even when signed, the public key is request-supplied and
/// never bound to the actor. Attacker signs with their own fresh key as "admin".
#[test]
fn nti_01b_signature_is_self_attested() {
    let mut e = TrustEngine::new();
    e.grant("admin", "payments");
    let attacker = SigningKey::from_bytes(&[9u8; 32]);
    let mut r = req("r1", "admin", "payments", serde_json::json!({}));
    r.public_key = Some(attacker.verifying_key().to_bytes().to_vec());
    r.signature = Some(attacker.sign(&r.message_to_sign()).to_bytes().to_vec());
    assert_eq!(e.evaluate(&r).decision, Decision::Allow);
}

/// (High) lib.rs:396-411 + 594-612 — MaxExecutions counts only the uncommitted `events`
/// buffer, which is drained every 10 records. Limit resets on each batch commit.
#[test]
fn nti_04_max_executions_resets_on_batch_commit() {
    let (sk, pk) = issuer();
    let mut e = TrustEngine::new();
    e.register_issuer_key("issuer", pk).unwrap();
    e.grant("issuer", "pay");
    e.grant("noise", "noise");
    let t = token(&sk, "tok-1", "pay", vec![caveat(CaveatType::MaxExecutions(1))]);

    let mut r = req("a", "anyone", "pay", serde_json::json!({}));
    r.token = Some(t.clone());
    assert_eq!(e.record(r.clone()).decision, Decision::Allow, "1st use");
    assert_eq!(e.record(r.clone()).decision, Decision::Deny, "2nd use blocked");

    // Two token events are buffered; 8 unrelated records reach 10 and trigger commit_batch.
    for i in 0..8 {
        e.record(req(&format!("n{i}"), "noise", "noise", serde_json::json!({})));
    }
    assert!(e.events.is_empty(), "buffer drained by commit");
    assert_eq!(e.record(r.clone()).decision, Decision::Allow, "limit bypassed after commit");
}

/// (High) lib.rs:412-420 — ValueLimit reads input["amount"].as_u64().unwrap_or(0).
/// Non-u64 encodings (string, float, negative) evaluate as 0 and pass. Currency is ignored.
#[test]
fn nti_05_value_limit_type_confusion() {
    let (sk, pk) = issuer();
    let mut e = TrustEngine::new();
    e.register_issuer_key("issuer", pk).unwrap();
    e.grant("issuer", "pay");
    let t = token(&sk, "tok-v", "pay", vec![caveat(CaveatType::ValueLimit(100, "NOK".into()))]);
    for amt in [
        serde_json::json!("1000000"),
        serde_json::json!(1000000.5),
        serde_json::json!(-1),
        serde_json::json!({"value": 1000000}),
    ] {
        let mut r = req("v", "x", "pay", serde_json::json!({ "amount": amt, "currency": "USD" }));
        r.token = Some(t.clone());
        assert_eq!(e.evaluate(&r).decision, Decision::Allow, "amount {amt} bypassed limit 100");
    }
}

/// (High) lib.rs:421-429 — PathRestricted is a raw prefix match; no normalization.
#[test]
fn nti_06_path_prefix_escape() {
    let (sk, pk) = issuer();
    let mut e = TrustEngine::new();
    e.register_issuer_key("issuer", pk).unwrap();
    e.grant("issuer", "file_management");
    let t = token(&sk, "tok-p", "file_management",
        vec![caveat(CaveatType::PathRestricted("/srv/app/data".into()))]);
    for p in ["/srv/app/data/../../../etc/passwd", "/srv/app/data_secret/key", "/srv/app/data/../.ssh/id_ed25519"] {
        let mut r = req("p", "x", "file_management", serde_json::json!({ "path": p }));
        r.token = Some(t.clone());
        assert_eq!(e.evaluate(&r).decision, Decision::Allow, "{p} escaped prefix");
    }
}

/// (High) lib.rs:712-759 — token is a pure bearer: no subject/delegate, actor never checked
/// in the token path. Stolen token works for any actor string.
#[test]
fn nti_08_token_is_unbound_bearer() {
    let (sk, pk) = issuer();
    let mut e = TrustEngine::new();
    e.register_issuer_key("issuer", pk).unwrap();
    e.grant("issuer", "pay");
    let t = token(&sk, "tok-b", "pay", vec![]);
    for actor in ["alice", "mallory", "", "issuer"] {
        let mut r = req("b", actor, "pay", serde_json::json!({}));
        r.token = Some(t.clone());
        assert_eq!(e.evaluate(&r).decision, Decision::Allow);
    }
}

/// (High) lib.rs:61-98, 712-759 — the token signature covers only id, issuer, capability and
/// caveats. One token authorizes any call identity and any arguments under that capability.
#[test]
fn nti_08b_token_not_bound_to_call() {
    let (sk, pk) = issuer();
    let mut e = TrustEngine::new();
    e.register_issuer_key("issuer", pk).unwrap();
    e.grant("issuer", "pay");
    let t = token(&sk, "tok-c", "pay", vec![]);
    for (id, input) in [
        ("c1", serde_json::json!({ "to": "acct-A", "amount": 1 })),
        ("c2", serde_json::json!({ "to": "acct-Z", "amount": 999 })),
    ] {
        let mut r = req(id, "issuer", "pay", input);
        r.token = Some(t.clone());
        assert_eq!(e.evaluate(&r).decision, Decision::Allow, "call {id} authorized by unbound token");
    }
}

/// (High) lib.rs:846-850 — verify_history trusts `last_batch_hash` from the state file
/// instead of the recomputed chain head. Trailing committed batches can be deleted undetected.
#[test]
fn nti_07_audit_batch_truncation_undetected() {
    let mut e = TrustEngine::new();
    e.grant("a", "c");
    for i in 0..25 {
        e.record(req(&format!("r{i}"), "a", "c", serde_json::json!({})));
    }
    assert_eq!(e.batches.len(), 2);
    assert_eq!(e.events.len(), 5);
    assert!(e.verify_history());

    // Attacker with write access to the persisted JSON drops the most recent committed batch.
    e.batches.pop();
    assert!(e.verify_history(), "truncation of last committed batch passes verification");

    // Control: removing ALL batches is detected (pending-event anchor falls back to "").
    e.batches.clear();
    assert!(!e.verify_history(), "control: full removal detected");
}

/// (Critical for mesh) lib.rs:2012-2036, 2082-2088 — AirGapBundle carries its own signer key;
/// verify() never checks it against any trust anchor. Any key can push any state_root.
#[test]
fn nti_03_airgap_bundle_self_signed_trust() {
    let mut victim = TrustEngine::new();
    victim.grant("a", "c");
    for i in 0..10 {
        victim.record(req(&format!("r{i}"), "a", "c", serde_json::json!({})));
    }
    let attacker = SigningKey::from_bytes(&[42u8; 32]);
    let mut bundle = victim.export_airgap_bundle(Some(&attacker)).unwrap();
    bundle.state_merkle_root = "deadbeef".repeat(8); // forged state root
    bundle.signature = attacker.sign(&bundle.message_to_sign()).to_bytes().to_vec();

    let mut reg = DistributedRegistry { peers: Default::default(), state_root: "genesis".into() };
    assert!(reg.sync_state(bundle).is_ok(), "forged bundle accepted");
    assert_eq!(reg.state_root, "deadbeef".repeat(8));
}

/// (Medium) lib.rs:571-591 — Rust Merkle duplicates the odd node and has no leaf/node domain
/// separation: the exact weakness PR #62/#63 fixed in the Python generator. [h1,h2,h3] and
/// [h1,h2,h3,h3] produce the same root; AirGapBundle.verify() checks only the root.
#[test]
fn nti_11_merkle_odd_node_duplication_collision() {
    let mut e = TrustEngine::new();
    e.grant("a", "c");
    for i in 0..3 {
        e.record(req(&format!("r{i}"), "a", "c", serde_json::json!({})));
    }
    let sk = SigningKey::from_bytes(&[1u8; 32]);
    e.commit_batch();
    let b3 = e.export_airgap_bundle(Some(&sk)).unwrap();
    let mut b4 = b3.clone();
    b4.batch.events.push(b3.batch.events[2].clone()); // duplicate last event
    // Merkle root identical for 3 and 4 events -> root alone does not commit to the event set.
    let mut e4 = TrustEngine::new();
    e4.events = b4.batch.events.clone();
    let root4 = {
        // compute_merkle_root is private; replicate via commit_batch on a scratch engine
        e4.commit_batch();
        e4.batches[0].merkle_root.clone()
    };
    assert_eq!(root4, b3.batch.merkle_root);
}

/// (Medium) lib.rs:1142-1168 — revocation check is fail-open: a malformed/invalid revocation
/// signature causes the revoked credential to be ACCEPTED.
#[test]
fn nti_10_revocation_fail_open() {
    let vk = SigningKey::from_bytes(&[3u8; 32]);
    let mut layer = RecommendationLayer::new();
    layer.verifiers.insert("v1".into(), VerifierProfile {
        id: "v1".into(), tier: VerifierTier::Foundational,
        public_key: vk.verifying_key().to_bytes().to_vec(), reputation: 1.0,
    });
    let now = chrono::Utc::now();
    let mut cred = IndependentCredential {
        verifier_id: "v1".into(), standard: VerificationStandard::SOC2,
        evidence_hash: "ev1".into(), issued_at: now,
        expires_at: now + chrono::Duration::days(30), signature: vec![],
    };
    let msg = serde_json::to_vec(&serde_json::json!({
        "verifier_id": cred.verifier_id, "standard": cred.standard,
        "evidence_hash": cred.evidence_hash, "issued_at": cred.issued_at, "expires_at": cred.expires_at,
    })).unwrap();
    cred.signature = vk.sign(&msg).to_bytes().to_vec();
    assert!(layer.verify_credential(&cred));

    // Revocation notice present but with a garbage signature (e.g. corrupted/attacker-planted).
    layer.revocations.insert("ev1".into(), RevocationNotice {
        credential_hash: "ev1".into(), reason: "compromised".into(),
        timestamp: now, signature: vec![0u8; 64],
    });
    assert!(layer.verify_credential(&cred), "revoked credential still accepted (fail-open)");
}

/// (Medium) lib.rs:1769-1793 — handshake is unauthenticated: responder never checks the
/// initiator against the peer registry; the initiator verifies only against the self-reported
/// responder key (TOFU). Together: MITM.
#[test]
fn nti_09_handshake_accepts_unknown_peer() {
    let node = AgentMeshNode::new("node-a".into());
    let mallory = AgentMeshNode::new("mallory".into());
    let (reqst, _) = mallory.initiate_handshake();
    assert!(node.peers.is_empty());
    assert!(node.respond_to_handshake(&reqst).is_ok(), "secret derived with unregistered peer");
}

/// (High) lib.rs:1591-1611 — AutonomousAgent::execute_task dispatches through the orchestrator
/// first and evaluates intent policies afterwards. In FailSafe mode a violation is reported as
/// an error, but the forbidden file write has already happened. Real local effect in a temp dir.
#[test]
fn nti_13_intent_policy_checked_after_effect() {
    let dir = std::env::temp_dir().join(format!("aacp-nti-13-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let target = dir.join("forbidden.txt");
    let _ = std::fs::remove_file(&target);
    let path = target.to_str().unwrap().to_string();

    let mut engine = TrustEngine::new();
    engine.grant("agent", "file_management");
    let mut orch = Orchestrator::new(engine);
    orch.register_module(Box::new(SystemModule));
    let mut agent = AutonomousAgent::new("agent".into(), orch);
    assert_eq!(agent.safety_mode, SafetyMode::FailSafe);
    agent.add_policy(IntentPolicy {
        name: "no-forbidden-file".into(),
        capability: "file_management".into(),
        constraints: serde_json::json!({ "not_allowed_paths": [path.clone()] }),
    });
    let mut r = req("w1", "agent", "file_management", serde_json::json!({ "path": path, "content": "x" }));
    r.action = "write_file".into();

    let rt = tokio::runtime::Runtime::new().unwrap();
    let res = rt.block_on(agent.execute_task(r));
    let written = target.exists();
    let _ = std::fs::remove_dir_all(&dir);
    assert!(res.is_err(), "policy violation is reported");
    assert!(written, "the forbidden effect happened before the policy was checked");
}
