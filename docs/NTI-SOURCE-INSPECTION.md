# NTI source inspection

Inspected on 2026-11-08. This is a bounded source inspection of
[Neutral Trust Infrastructure](https://github.com/abisheakp197/Neutral-Trust-Infrastructure)
(NTI), not a complete audit, production assessment, AACP run or independent
execution of NTI. No NTI code was executed. The reproduction candidates in
[`nti-source-inspection/reproduction_candidates.rs`](nti-source-inspection/reproduction_candidates.rs)
were written from the source and have **not** been compiled or run.

Drafted by an AI agent (Claude) at the maintainer's request and reviewed by the
maintainer before publication. Producer review: not yet requested. Unresolved
disagreement will be published alongside this record, not edited away.

## Pins

| Subject | Pin |
| :--- | :--- |
| Repository HEAD | [`de08dbdcd27e01c27585d936091c69b59d173a97`](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/tree/de08dbdcd27e01c27585d936091c69b59d173a97) |
| PR #63 merge | [`44d55490e90d5734e44b114ef1680d4ca4c0a71a`](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/commit/44d55490e90d5734e44b114ef1680d4ca4c0a71a) (`ea763c0` + `0b30c52`) |
| Witness manifest | `conformance/witness/MANIFEST.json` v5, `commit: ea763c0c…`, signing key fingerprint `bab37667…c009` |
| Generator | `conformance/witness_generator/generate_seals.py`, sha256 `a7ee4a2f7b86c117…` (matches manifest) |

Line numbers below refer to the HEAD pin. `L` = `ube-foundation/src/lib.rs`,
`N` = `ube-foundation/src/network.rs`, `G` = the generator.

## Scope and method

Read in full: `lib.rs` (2104 lines), `network.rs`, `generate_seals.py`,
`conformance/witness/{MANIFEST,RESULTS}.json`, `verify.sh` (targeted), the
integration-test names. Manifest hashes for the generator, sample evidence,
tests and `Cargo.{toml,lock}` were recomputed and match HEAD. One digest claim
(P-01) was reproduced by hashing a fixed string; nothing else was executed.

Severity is judged against NTI's own stated properties ("zero-trust",
"fail-closed", independently verifiable witness evidence). The HTTP API binds
to `127.0.0.1` (`N:136`), so network findings are reachable by local processes
or via SSRF, not directly from the internet.

## Engine findings

Each candidate ID maps to a test function of the same name in the reproduction
file. "Static" means the conclusion rests on reading, not execution.

| ID | Sev. | Location | Observation |
| :--- | :--- | :--- | :--- |
| NTI-01 | Critical | `L:685-776`, `N:46-59` | `actor` is an unauthenticated string. `signature`, `public_key`, `pqc_*`, `identity_claim` are optional and skipped when absent; the decision is `capabilities[actor] ∋ capability`. When present, the public key is request-supplied and never bound to the actor (no actor→key registry exists). `IdentityClaim` is likewise self-signed. |
| NTI-02 | Critical¹ | `N:83-133` | `POST /vote` signs an `Allow` `ConsensusVote` for any unauthenticated proposal. The local check is `IntentVerifier` with empty constraints, which returns `Valid` for every action except constrained `write_file`. `engine.evaluate` is never called. Vote messages (`L:102-110`) carry no nonce or epoch, so votes replay. Result: `verify_consensus` (`L:136-169`) is satisfiable at any threshold by collecting votes. Static. |
| NTI-03 | Critical¹ | `L:2012-2036`, `L:2082-2088` | `AirGapBundle::verify` checks the signature against the key carried in the bundle. `DistributedRegistry::sync_state` then overwrites `state_root`. Any key can install any state root. |
| NTI-04 | High | `L:396-411`, `L:594-612`, `L:801-803` | `MaxExecutions` counts only the uncommitted `events` buffer, which `commit_batch` drains at 10 records. The limit resets after each commit. |
| NTI-05 | High | `L:412-420` | `ValueLimit` reads `input["amount"].as_u64().unwrap_or(0)`. String, float, negative or object amounts evaluate to 0 and pass. The caveat's currency is ignored. |
| NTI-06 | High | `L:421-429`, `L:1433-1440`, sink `L:1463-1469` | `PathRestricted` is a raw `starts_with` with no normalisation (`prefix/../..`, `prefix_sibling`). `not_allowed_paths` is exact string equality. |
| NTI-07 | High | `L:846-850` | `verify_history` anchors pending events to the persisted `last_batch_hash` and never compares it with the recomputed batch-chain head. Trailing committed batches can be removed from the state file while pending events remain, and `load_from_file` accepts it. (Removing *all* batches is detected: the anchor then becomes `""`.) |
| NTI-08 | High | `L:61-98`, `L:712-759` | Capability tokens have no subject or audience. The token branch never examines `request.actor` and returns `Allow` before the actor capability check. A token is a bearer credential for any actor string. |
| NTI-09 | Medium | `L:1769-1793`, `N:140-188` | Handshake is unauthenticated: the responder ignores `self.peers`; the initiator verifies the response against the self-reported responder key (TOFU). The signature covers only the two ephemeral keys, not identities or a transcript. |
| NTI-10 | Medium | `L:1142-1168` | Revocation is fail-open: a revocation notice whose signature does not verify is ignored and the credential is accepted. A malformed verifier key becomes `[0; 32]` via `unwrap_or`. |
| NTI-11 | Medium | `L:571-591` | The engine's audit Merkle root duplicates the odd node and has no leaf/node domain separation, so `[h1,h2,h3]` and `[h1,h2,h3,h3]` share a root. PR #62/#63 describe and fix exactly this in the Python generator only. `AirGapBundle::verify` checks the root alone. |
| NTI-12 | Low | various | `verify` vs `verify_strict` used inconsistently (only `CapabilityToken` is strict); `register_voter_key` accepts unvalidated bytes; every `message_to_sign` maps serialization errors to empty bytes (`unwrap_or_default`); `verify_consensus(threshold = 0)` is always true; `Orchestrator` defaults to `consensus_threshold = 1`; `SafetyMode::FailOpen` continues after policy violations; `PqcKeyPair` derives `Serialize` with secret key bytes; `NetworkModule` sends unsigned requests and depends on NTI-01 to work. Static. |

¹ Critical relative to the mesh/consensus claims; exposure is limited by the
loopback bind noted above.

What the inspection did not find fault with: the primitive calls to Ed25519,
Dilithium5, Kyber1024 and ChaCha20-Poly1305 (random 96-bit nonce per KEM
encapsulation, so nonce reuse under one key is not a concern).

## PR #63 provenance claims

PR #63 is titled "close five provenance gaps (key history, generator commit,
bound suite evidence)". Genuinely improved: the package signature is
domain-separated and length-prefixed; the generator's S5 Merkle follows RFC 6962
with domain separation; S6 binds root, leaf count and ordered names; manifest
file hashes match the tree.

| ID | Sev. | Location | Observation |
| :--- | :--- | :--- | :--- |
| P-01 | High | `G:154-156`, `G:184-186`; manifest `suite_evidence_logs.cargo_build`, `.cargo_check_python` | Build and check transcripts are canonicalised to `finished=<bool>\nerror_lines=<n>\n`. For any successful build of any crate the digest is `sha256("finished=True\nerror_lines=0\n")` = `08344a03a3788eec6baf26a976eb3e99799736cd4d0f4f6a439e4c5d416efe20`, which is the value recorded for both suites. **Reproduced** by hashing the string. These digests bind no NTI-specific fact. |
| P-02 | High | `G:110-123`, `G:174-183` | The test digest binds sorted test names and statuses, not code. `src/lib.rs`, `src/network.rs` and `src/python_bindings.rs` are absent from `nti_test_scripts`. `manifest.commit` is an unsigned-by-construction string the verifier never compares with the checked-out tree. The package shows that tests with these names passed on some tree, not that the published engine passed them. |
| P-03 | Medium | `G:434-469`, `G:483` | `--skip-suite-runs` reuses earlier suite evidence while stamping the current `HEAD` and a new timestamp. Nothing records the commit on which the evidence was produced. |
| P-04 | Medium | `G:77-108`, `G:352-385`; `verify.sh:33,91,128` | `key_history` is written into the manifest and signed by the current key; four keys in about 34 hours, none cross-signed by its predecessor, all "private key not retained". Whoever controls the generator can append a key with an equally valid history. `key_url` is served from the same repository's Pages, and `verify.sh` reads the local `PUBLIC_KEY.pem`, never the URL. |
| P-05 | Low | `G:493`; `verify.sh:205-214` | Python test totals are hard-coded (`2 if py_ok else 0`). When cargo is missing, `verify.sh` skips the suite step and still prints a success-worded `RESULT` line. |

## Reproduction candidates

[`nti-source-inspection/reproduction_candidates.rs`](nti-source-inspection/reproduction_candidates.rs)
contains one Rust integration test per engine finding NTI-01 to NTI-11 (except
NTI-02 and NTI-12, which are HTTP-level or hygiene and remain static). Each test
is written to **pass when the weakness is present**. To run against the pin:

```sh
git clone https://github.com/abisheakp197/Neutral-Trust-Infrastructure nti
git -C nti checkout de08dbdcd27e01c27585d936091c69b59d173a97
cp docs/nti-source-inspection/reproduction_candidates.rs nti/ube-foundation/tests/
cd nti/ube-foundation && cargo test --locked --test reproduction_candidates
```

Until that run is recorded, every engine finding is a candidate: a compile
error or a failing test means the candidate is wrong or the pin differs, not
that NTI is broken in a different way.

## AACP relationship

No AACP run was performed and no NTI claim is mapped to an AACP property. NTI's
witness vocabulary (S4/S5/S6, `PASSED`) is preserved as NTI's own. Mapping
status for every AACP property: `not_evaluated`.

## Remaining boundaries

The inspection did not execute NTI's suites, `verify.sh` or the reproduction
candidates; did not inspect `python_bindings.rs`, the conformance fixtures under
`conformance/agent-did-interop/` and `conformance/vate-recovery/` beyond file
listing, or the CI workflows; did not test the HTTP API live; and did not
assess dependencies. A hash match establishes byte identity, not authenticity
or execution. NTI's own description of its threat model may narrow some
severities; that requires producer input.
