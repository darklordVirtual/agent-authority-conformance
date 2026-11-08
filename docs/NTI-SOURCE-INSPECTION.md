# NTI source inspection

Inspected and executed on 2026-11-08. This is a bounded inspection of
[Neutral Trust Infrastructure](https://github.com/abisheakp197/Neutral-Trust-Infrastructure)
(NTI) at `de08dbd`. It combines two sweeps: the Claude Mythos sweep (findings
NTI-01 to NTI-12, P-01 to P-05) and the OpenAI Daybreak source checks
(`nti_security_checks.ps1`, four checks). Both are encoded as
[AACP controls](CONTROLS.md), so a new run against NTI, or a binding for
another project, produces the same kind of A-G report. It is not a complete
audit or a production assessment.

- **Generated report:** [`reports/nti-de08dbd/REPORT.md`](../reports/nti-de08dbd/REPORT.md)
- **Assessment (schema v0.1):** [`examples/nti-de08dbd.json`](../examples/nti-de08dbd.json)
- **Binding:** [`controls/bindings/nti-de08dbd/`](../controls/bindings/nti-de08dbd/), catalog
  [`controls/aacp-controls-v1/catalog.json`](../controls/aacp-controls-v1/catalog.json)
- **CI reproduction:** [`.github/workflows/controls.yml`](../.github/workflows/controls.yml)

Drafted and executed by an AI agent (Claude) at the maintainer's request; the
maintainer authorized executing NTI code in a disposable environment and
publishing the result. Producer review: not yet requested. Unresolved
disagreement will be published alongside this record, not edited away.

## Result

| Property | Status | Controls counted |
| :--- | :--- | :--- |
| A Receipt Integrity | **FAIL** | AACP-A-01 use limit resets after batch commit |
| B Authority Provenance | **FAIL** | AACP-B-01 unauthenticated actor, B-02 self-attested key, B-03 bearer token |
| C Exact-Call Integrity | **FAIL** | AACP-C-01 token not bound to the call |
| D Semantic Authority | **FAIL** | AACP-D-01 value-limit type confusion, D-02 path escape, D-03 policy checked after the effect |
| E Execution-Boundary Integrity | UNTESTED | none |
| F TOCTOU Resistance | UNTESTED | none |
| G Effect Verification | UNTESTED | none |

The rows are not commensurable and are not combined (SPECIFICATION §7). Every
counted control is an executed probe that reproduces the weakness on the
pinned revision and stops reproducing it when that weakness alone is repaired.
Static probes and controls outside A-G are reported in
[REPORT.md](../reports/nti-de08dbd/REPORT.md) without affecting a status.

## Why these are A, B, C and D failures

A weakness is not automatically a failure of a nearby property. Each counted
control carries a normative basis in the catalog (SPECIFICATION §2 text,
rationale and boundary), printed in the
[report](../reports/nti-de08dbd/REPORT.md#normative-basis-of-counted-controls).
For the two least obvious mappings:

- **AACP-A-01 → A.** A's scope names *single-use semantics* and asks whether the
  artifact is *currently valid*. NTI's `MaxExecutions` is a caveat inside the
  signed token, so the limit belongs to the authorization artifact. A
  `MaxExecutions(1)` token accepted a second time is not currently valid.
  Quotas outside the artifact would not be A (rate limiting is outside the
  model, §10).
- **AACP-C-01 → C.** C asks whether the authorization is bound to the exact call
  and names call identity, target and full argument binding. NTI accepts a
  call authorized by the token alone: the request signature that would bind
  the call is optional, and the probe sends none. Were call binding enforced
  elsewhere on the mandatory path, or tokens declared as capabilities without
  call binding, this would not be a C failure; the latter would make the row
  `OUT_OF_SCOPE`.

These mappings are the assessor's. The implementer may contest them, and the
disagreement would be recorded (SPECIFICATION §8).

## Provenance of the result

The committed report comes from an `AUTHOR_RUN`: the assessor wrote the probes
and repairs and ran them. The CI run is a `REPRODUCTION` with the same probes
on a clean runner. It shows the result is repeatable, not that the probes are
right. Neither is an independent security review, and the implementer has not
reviewed either.

## Sweep to control mapping

| Finding | Origin | Control | Probe(s) | Basis | AACP |
| :--- | :--- | :--- | :--- | :--- | :--- |
| NTI-01 | Mythos | AACP-B-01 | P-B-01 | executed, discriminates | B exact |
| NTI-01b | Mythos | AACP-B-02 | P-B-02 | executed, discriminates | B exact |
| NTI-02 | Mythos | AACP-B-04, AACP-A-04 | S-B-04, S-A-04 | static | exact, not counted |
| NTI-03 | Mythos | AACP-A-03 | P-A-03 | executed, discriminates | A structural |
| NTI-04 | Mythos | AACP-A-01 | P-A-01 | executed, discriminates | A exact |
| NTI-05 | Mythos | AACP-D-01 | P-D-01 | executed, discriminates | D exact |
| NTI-06 | Mythos | AACP-D-02 | P-D-02 | executed, discriminates | D exact |
| NTI-07 | Mythos | AACP-X-01 | P-X-01 | executed, discriminates | no_mapping |
| NTI-08 | Mythos + Daybreak #1 | AACP-B-03 | P-B-03, S-B-03 | executed and static, both discriminate | B exact |
| NTI-08b | Mythos | AACP-C-01 | P-C-01 | executed, discriminates | C exact |
| NTI-09 | Mythos | AACP-X-03 | P-X-03 | executed, discriminates | no_mapping |
| NTI-10 | Mythos | AACP-A-02 | P-A-02 | executed, discriminates | A partial |
| NTI-11 | Mythos | AACP-X-02 | P-X-02 | executed, discriminates | no_mapping |
| NTI-12 | Mythos | none | none | static hygiene, not a control | none |
| NTI-13 | Daybreak #2 | AACP-D-03 | P-D-03, S-D-03 | executed with a real file write, and static; both discriminate | D exact |
| P-01 | Mythos | AACP-EV-01 | S-EV-01 | static, digest reproduced | no_mapping |
| P-02 | Mythos + Daybreak #4 | AACP-EV-02 | S-EV-02 | static | no_mapping |
| P-03 | Mythos | AACP-EV-03 | S-EV-03 | static | no_mapping |
| P-04 | Mythos + Daybreak #3 | AACP-EV-04 | S-EV-04 | static | no_mapping |
| P-05 | Mythos | AACP-EV-05 | S-EV-05 | static | no_mapping |

NTI-13 is new from Daybreak: `AutonomousAgent::execute_task` (`L:1591-1611`)
dispatches through the orchestrator and only then evaluates intent policies.
In `FailSafe` mode the violation is returned as an error, but the forbidden
`write_file` has already happened. P-D-03 shows this with a real write in a
temporary directory; the repair (evaluate policies before dispatch) stops it.

Daybreak #4 ("witness matches HEAD: false") is not a weakness by itself, since a
package is generated before it is committed. It is part of AACP-EV-02
together with the unattested source and the verifier's missing commit check.

## Pins

| Subject | Pin |
| :--- | :--- |
| Repository HEAD | [`de08dbdcd27e01c27585d936091c69b59d173a97`](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/tree/de08dbdcd27e01c27585d936091c69b59d173a97) |
| Pinned files | `lib.rs`, `network.rs`, `generate_seals.py`, `witness/verify.sh`, `witness/MANIFEST.json` by SHA-256 in `binding.json` |
| PR #63 merge | [`44d55490e90d5734e44b114ef1680d4ca4c0a71a`](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/commit/44d55490e90d5734e44b114ef1680d4ca4c0a71a) (`ea763c0` + `0b30c52`) |
| Witness manifest | `conformance/witness/MANIFEST.json` v5, `commit: ea763c0c…`, signing key fingerprint `bab37667…c009` |
| Toolchain | rustc/cargo 1.97.0, `--locked` |

Line numbers refer to the HEAD pin. `L` = `ube-foundation/src/lib.rs`,
`N` = `ube-foundation/src/network.rs`, `G` = `conformance/witness_generator/generate_seals.py`.

## Reproduce

```sh
git clone https://github.com/abisheakp197/Neutral-Trust-Infrastructure nti
git -C nti checkout de08dbdcd27e01c27585d936091c69b59d173a97
python -m conformance.controls run --binding controls/bindings/nti-de08dbd --subject nti \
    --out out/result.json --run-id my-run --operator "<you>" --independence REPRODUCTION
python -m conformance.controls compare reports/nti-de08dbd/results/$(cat reports/nti-de08dbd/CURRENT) out/result.json
```

This compiles and runs NTI code: use a disposable environment. Or run the
`AACP controls` workflow from the Actions tab.

## Finding detail

| ID | Sev. | Location | Observation |
| :--- | :--- | :--- | :--- |
| NTI-01 | Critical | `L:685-776`, `N:46-59` | `actor` is an unauthenticated string. Signature, key, PQC and identity-claim fields are optional and skipped when absent; the decision is `capabilities[actor] ∋ capability`. When present, the public key comes from the request and is never bound to the actor. |
| NTI-01b | Critical | `L:685-710` | A request signed by any fresh key while naming a granted actor is allowed. |
| NTI-02 | Critical¹ | `N:83-133` | `POST /vote` signs an `Allow` vote for any unauthenticated proposal; the local check is `IntentVerifier` with empty constraints and `evaluate()` is never called; vote messages (`L:100-110`) have no nonce. |
| NTI-03 | Critical¹ | `L:2012-2036`, `L:2082-2088` | `AirGapBundle::verify` trusts the key carried in the bundle; `sync_state` installs any self-signed state root. |
| NTI-04 | High | `L:396-411`, `L:594-612` | `MaxExecutions` counts only the uncommitted buffer, drained at 10 records. |
| NTI-05 | High | `L:412-420` | `ValueLimit` reads `amount` with `as_u64().unwrap_or(0)`; non-integer encodings pass; currency ignored. |
| NTI-06 | High | `L:421-429`, `L:1433-1440` | `PathRestricted` is a raw `starts_with`; `not_allowed_paths` is exact equality. |
| NTI-07 | High | `L:846-850` | `verify_history` never compares the persisted `last_batch_hash` with the recomputed chain head; trailing committed batches can be removed. Removing all batches is detected. |
| NTI-08 | High | `L:61-98`, `L:712-759` | Tokens have no subject; the token path never checks `request.actor`. |
| NTI-08b | High | `L:76-81` | The token signature covers id, issuer, capability and caveats only. |
| NTI-09 | Medium | `L:1769-1793`, `N:140-188` | Handshake responder ignores the peer registry; initiator verifies against the self-reported key (TOFU). |
| NTI-10 | Medium | `L:1142-1168` | Revocation of marketplace credentials fails open when the notice signature does not verify. |
| NTI-11 | Medium | `L:571-591` | The engine's audit Merkle root duplicates the odd node; PR #62/#63 fix this only in the Python generator. |
| NTI-12 | Low | various | `verify` vs `verify_strict` inconsistent; unvalidated voter keys; `message_to_sign` maps errors to empty bytes; `verify_consensus(threshold = 0)` is true; default `consensus_threshold = 1`; `SafetyMode::FailOpen`; `PqcKeyPair` serializes secret keys. |
| NTI-13 | High | `L:1591-1611`, sink `L:1463-1469` | Intent policies are evaluated after dispatch; in `FailSafe` mode the forbidden effect has already occurred when the error is returned. |
| P-01 | High | `G:149-186` | Build and check digests equal `sha256("finished=True\nerror_lines=0\n")` = `08344a03…`, which binds nothing about NTI. |
| P-02 | High | `G:110-123`, `G:174-183` | The test digest binds names and statuses, not code; `src/*.rs` are not attested; `verify.sh` never compares `manifest.commit` with the checkout. |
| P-03 | Medium | `G:434-483` | `--skip-suite-runs` reuses earlier evidence while stamping the current `HEAD`. |
| P-04 | Medium | `G:77-108`, `G:352-385`, `verify.sh` | `key_history` is self-certifying; `verify.sh` reads the packaged key and never the declared `key_url`. |
| P-05 | Low | `G:493`, `verify.sh:205-214` | Python totals are hard-coded; without cargo, `verify.sh` still prints a success-worded `RESULT`. |

¹ Critical relative to the mesh and consensus claims; the HTTP API binds to
`127.0.0.1` (`N:136`).

Not faulted: the primitive calls to Ed25519, Dilithium5, Kyber1024 and
ChaCha20-Poly1305. PR #63 genuinely improved the package signature (domain
separation, length prefixes), the generator's RFC 6962 Merkle tree and the S6
binding; NTI's `PASSED` claims remain `REPORTED` producer evidence for AACP.

## History

The first two author runs used an NTI-specific script that preceded the
generic controls; they are kept in
[`nti-source-inspection/results/`](nti-source-inspection/results/) with a note.
Their findings are a subset of the current run's.

## Remaining boundaries

Not done: the HTTP API, Python bindings and multi-node operation were not
exercised at runtime; NTI-02 and the P-series rest on static probes; NTI-12 is
not a control; E, F and G have no probes; `conformance/agent-did-interop/`,
`conformance/vate-recovery/` and the CI workflows were not inspected;
dependencies were not assessed. Probes and repairs are the assessor's, so no
run is independent. The implementer has supplied no scope declaration; if NTI
declares a narrower scope, some rows may become `OUT_OF_SCOPE` rather than
`FAIL`.
