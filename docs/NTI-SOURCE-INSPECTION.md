# NTI source inspection

Inspected and executed on 2026-11-08. This is a bounded inspection of
[Neutral Trust Infrastructure](https://github.com/abisheakp197/Neutral-Trust-Infrastructure)
(NTI): a source reading, plus an AACP assessment of the library API backed by
executed, discriminating tests. It is not a complete audit or a production
assessment.

- **AACP assessment (A-G):** [`examples/nti-de08dbd.json`](../examples/nti-de08dbd.json)
- **Procedure:** [`scripts/run_nti_inspection.py`](../scripts/run_nti_inspection.py) with
  [`reproduction_candidates.rs`](nti-source-inspection/reproduction_candidates.rs),
  [`mutations.json`](nti-source-inspection/mutations.json) and
  [`expected.json`](nti-source-inspection/expected.json)
- **Result records:** [`nti-source-inspection/results/`](nti-source-inspection/results/)
- **CI reproduction:** [`.github/workflows/nti-inspection.yml`](../.github/workflows/nti-inspection.yml)

Drafted and executed by an AI agent (Claude) at the maintainer's request; the
maintainer authorized executing NTI code in a disposable environment and
publishing the result. Producer review: not yet requested. Unresolved
disagreement will be published alongside this record, not edited away.

## Result

| Property | Status | Basis |
| :--- | :--- | :--- |
| A Receipt Integrity | **FAIL** | Single-use semantics: a `MaxExecutions(1)` token is accepted again after a batch commit (NTI-04). |
| B Authority Provenance | **FAIL** | Actor is unauthenticated (NTI-01), signing key is self-attested (NTI-01b), tokens have no subject (NTI-08). |
| C Exact-Call Integrity | **FAIL** | One token authorizes calls with different identities, targets and amounts (NTI-08b). |
| D Semantic Authority | **FAIL** | `ValueLimit` and `PathRestricted` caveats are bypassed (NTI-05, NTI-06). |
| E Execution-Boundary Integrity | UNTESTED | §12 topology and bypass attempts not performed. |
| F TOCTOU Resistance | UNTESTED | Not exercised. |
| G Effect Verification | UNTESTED | Not exercised. |

The rows are not commensurable and are not to be combined (SPECIFICATION §7).
Each `FAIL` row names its supported condition and what it does not establish
in the assessment file; for example A's row does not show that token
signatures can be forged.

### How a FAIL row is established

For each weakness the procedure checks two things:

1. **Baseline:** on the pristine pinned revision the candidate test passes,
   so the weakness is present.
2. **Discrimination:** with a minimal repair of that one weakness applied to a
   fresh copy of `lib.rs`, the same test fails. A test that would pass whether
   or not the weakness exists is therefore not counted (SPECIFICATION §5).
   A build error under a mutation is recorded as `BUILD_ERROR`, never as
   discrimination.

The mutations are minimal repairs for measurement, not proposed patches.

The harness was checked negatively: a no-op mutation is reported
`DOES_NOT_DISCRIMINATE`, and a checkout at the wrong revision is a
`NON_VERDICT` with no verdict written. CI repeats both self-tests on every run.

### Runs

| Run | Independence | Result |
| :--- | :--- | :--- |
| [`2026-11-08-local-author-run-2.json`](nti-source-inspection/results/2026-11-08-local-author-run-2.json), procedure `e3d8c86` | `AUTHOR_RUN` (assessor wrote the tests and ran them) | `EXPECTATIONS_MET`: 12/12 baseline tests as expected, 11/11 mutations discriminate. **Current.** |
| CI, [`nti-inspection.yml`](../.github/workflows/nti-inspection.yml) on procedure `e3d8c86` | `REPRODUCTION` (same procedure, separate host and toolchain install) | CI_RUN_PENDING |
| [`2026-11-08-local-author-run.json`](nti-source-inspection/results/2026-11-08-local-author-run.json), procedure `9eaf002` | `AUTHOR_RUN` | `EXPECTATIONS_MET`, same baseline digest `daa0a7c3…`. Superseded: its harness crashed in the CI no-op self-test (fixed in `e3d8c86`). The CI reproduction of that procedure, [run 42479173368](https://github.com/darklordVirtual/agent-authority-conformance/actions/runs/42479173368), also reported `EXPECTATIONS_MET` before the self-test step failed. |

Neither run is an independent implementation; both execute assessor-authored
tests.

## Pins

| Subject | Pin |
| :--- | :--- |
| Repository HEAD | [`de08dbdcd27e01c27585d936091c69b59d173a97`](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/tree/de08dbdcd27e01c27585d936091c69b59d173a97) |
| Subject file | `ube-foundation/src/lib.rs`, sha256 `970a7bbda6568a3837e75562f59e5465aa6a6a0444bf9ddafea7608c76313466` |
| PR #63 merge | [`44d55490e90d5734e44b114ef1680d4ca4c0a71a`](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/commit/44d55490e90d5734e44b114ef1680d4ca4c0a71a) (`ea763c0` + `0b30c52`) |
| Witness manifest | `conformance/witness/MANIFEST.json` v5, `commit: ea763c0c…`, signing key fingerprint `bab37667…c009` |
| Generator | `conformance/witness_generator/generate_seals.py`, sha256 `a7ee4a2f7b86c117…` (matches manifest) |
| Toolchain (local run) | rustc 1.97.0, cargo 1.97.0, `--locked` |

Line numbers below refer to the HEAD pin. `L` = `ube-foundation/src/lib.rs`,
`N` = `ube-foundation/src/network.rs`, `G` = the generator.

## Reproduce

```sh
git clone https://github.com/abisheakp197/Neutral-Trust-Infrastructure nti
git -C nti checkout de08dbdcd27e01c27585d936091c69b59d173a97
python scripts/run_nti_inspection.py --nti nti \
    --out out/result.json --run-id my-run --operator "<you>" --independence REPRODUCTION
```

This compiles and runs NTI code: use a disposable environment. Exit status 0
means every expectation in `expected.json` held. Or run the workflow from the
Actions tab (`workflow_dispatch`).

## Findings and mapping

`Executed` = reproduced by a candidate test that also discriminates under its
mutation. `Static` = from reading only. The relationship column uses the
vocabulary of FEDERATION-REVIEW-PROTOCOL §5; only `Executed` rows with an
`exact` relationship produce an A-G status.

| ID | Sev. | Location | Basis | AACP | Observation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| NTI-01 | Critical | `L:685-776`, `N:46-59` | Executed (M-01) | B exact | `actor` is an unauthenticated string. Signature, key, PQC and identity-claim fields are optional and skipped when absent; the decision is `capabilities[actor] ∋ capability`. When present, the public key comes from the request and is never bound to the actor. |
| NTI-01b | Critical | `L:685-710` | Executed (M-01) | B exact | A request signed by any fresh key while naming a granted actor is allowed. |
| NTI-02 | Critical¹ | `N:83-133` | Static | A, B structural | `POST /vote` signs an `Allow` vote for any unauthenticated proposal; local check is `IntentVerifier` with empty constraints; vote messages (`L:102-110`) have no nonce, so votes replay. `verify_consensus` (`L:136-169`) is satisfiable by collecting votes. |
| NTI-03 | Critical¹ | `L:2012-2036`, `L:2082-2088` | Executed (M-03) | A structural | `AirGapBundle::verify` trusts the key carried in the bundle; `sync_state` installs any self-signed state root. A state-sync artifact, not an authorization artifact, so no A status. |
| NTI-04 | High | `L:396-411`, `L:594-612` | Executed (M-04) | A exact | `MaxExecutions` counts only the uncommitted buffer, drained at 10 records. |
| NTI-05 | High | `L:412-420` | Executed (M-05) | D exact | `ValueLimit` reads `amount` with `as_u64().unwrap_or(0)`; non-integer encodings pass; currency ignored. |
| NTI-06 | High | `L:421-429`, `L:1433-1440` | Executed (M-06) | D exact | `PathRestricted` is a raw `starts_with` (`../`, sibling prefixes); `not_allowed_paths` is exact equality. |
| NTI-07 | High | `L:846-850` | Executed (M-07) | no_mapping | `verify_history` never compares the persisted `last_batch_hash` with the recomputed chain head; trailing committed batches can be removed. Removing all batches is detected. |
| NTI-08 | High | `L:61-98`, `L:712-759` | Executed (M-08) | B exact | Tokens have no subject; the token path never checks `request.actor`. |
| NTI-08b | High | `L:76-81` | Executed (M-08b) | C exact | The token signature covers id, issuer, capability and caveats only; one token authorizes any call identity and arguments. |
| NTI-09 | Medium | `L:1769-1793`, `N:140-188` | Executed (M-09) | no_mapping | Handshake responder ignores the peer registry; initiator verifies against the self-reported key (TOFU); signature covers only ephemeral keys. |
| NTI-10 | Medium | `L:1142-1168` | Executed (M-10) | A partial | Revocation of marketplace credentials fails open when the notice signature does not verify; malformed verifier keys become `[0; 32]`. |
| NTI-11 | Medium | `L:571-591` | Executed (M-11) | no_mapping | The engine's audit Merkle root duplicates the odd node with no domain separation, so `[h1,h2,h3]` and `[h1,h2,h3,h3]` share a root. PR #62/#63 fix this only in the Python generator. |
| NTI-12 | Low | various | Static | no_mapping | `verify` vs `verify_strict` inconsistent; unvalidated voter keys; `message_to_sign` maps errors to empty bytes; `verify_consensus(threshold = 0)` is true; default `consensus_threshold = 1`; `SafetyMode::FailOpen`; `PqcKeyPair` serializes secret keys; `NetworkModule` sends unsigned requests. |

¹ Critical relative to the mesh and consensus claims; the HTTP API binds to
`127.0.0.1` (`N:136`), so it is reachable by local processes or via SSRF.

Not faulted: the primitive calls to Ed25519, Dilithium5, Kyber1024 and
ChaCha20-Poly1305.

## PR #63 provenance claims

PR #63 is titled "close five provenance gaps (key history, generator commit,
bound suite evidence)". Genuinely improved: the package signature is
domain-separated and length-prefixed; the generator's S5 Merkle follows RFC 6962
with domain separation; S6 binds root, leaf count and ordered names; manifest
file hashes match the tree.

For AACP, NTI's witness package is producer evidence. Its `PASSED` claims are
`REPORTED`, not `RESOLVED`, and the assessment does not rely on them. These
observations are `no_mapping` to A-G.

| ID | Sev. | Location | Basis | Observation |
| :--- | :--- | :--- | :--- | :--- |
| P-01 | High | `G:154-156`, `G:184-186`; manifest `suite_evidence_logs.cargo_build`, `.cargo_check_python` | Reproduced (hash of fixed string) | Build and check transcripts are canonicalised to `finished=<bool>\nerror_lines=<n>\n`. For any successful build of any crate the digest is `sha256("finished=True\nerror_lines=0\n")` = `08344a03a3788eec6baf26a976eb3e99799736cd4d0f4f6a439e4c5d416efe20`, the value recorded for both suites. |
| P-02 | High | `G:110-123`, `G:174-183` | Static | The test digest binds sorted test names and statuses, not code. `src/*.rs` are absent from `nti_test_scripts`. `verify.sh` never compares `manifest.commit` with the checked-out tree. |
| P-03 | Medium | `G:434-469`, `G:483` | Static | `--skip-suite-runs` reuses earlier suite evidence while stamping the current `HEAD`; the producing commit is not recorded. |
| P-04 | Medium | `G:77-108`, `G:352-385`; `verify.sh:33,91,128` | Static | `key_history` is self-certifying: written into the manifest and signed by the current key; four keys in about 34 hours, none cross-signed. `key_url` is in the same repository's Pages, and `verify.sh` reads the local key, never the URL. |
| P-05 | Low | `G:493`; `verify.sh:205-214` | Static | Python test totals are hard-coded; without cargo, `verify.sh` skips the suites and still prints a success-worded `RESULT`. |

## Remaining boundaries

Not done: the HTTP API, Python bindings and multi-node operation were not
exercised; NTI-02, NTI-12 and P-02 to P-05 rest on reading only; E, F and G have
no evidence; `conformance/agent-did-interop/`, `conformance/vate-recovery/` and
the CI workflows were listed, not inspected; dependencies were not assessed.
The tests and mutations are the assessor's, so neither run is independent. A
hash match establishes byte identity, not authenticity. The implementer has
supplied no scope declaration or non-claims; if NTI declares a narrower scope,
some rows may become `OUT_OF_SCOPE` rather than `FAIL`.
