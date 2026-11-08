# nti-witness

**Independence:** SECOND_IMPLEMENTATION. A reproduction made with knowledge of the producer's code; not independent verification.

Reads as `SECOND_IMPLEMENTATION` in federation-run-v1 and BCR-2 in BCR terms.

**Independence statement:** The checks in verifier/nti_witness.py were written by the runner from the pinned README, after reading the producer's verify.sh and generate_seals.py; no producer code is imported or executed and Ed25519 is the runner's own RFC 8032 implementation. Because the producer's code was read first, this is labelled SECOND_IMPLEMENTATION, not INDEPENDENT_IMPLEMENTATION.

**Roles:** verifier or adapter authored by darklordVirtual; run operated by Agent Authority Conformance (darklordVirtual); subject maintained by Neutral Trust Infrastructure (NTI) (abisheakp197); Neutral Trust Infrastructure (NTI) (abisheakp197).

**Trust material:**

- PUBLIC_KEY.pem as committed at each pinned commit. It has no external trust anchor, so a valid signature establishes integrity under that key, not who holds it.

**Procedure:** `nti-witness-readme-how-to-verify: the README steps, run with the runner's own checks`.

**Track:** self-service over a pinned public boundary (https://github.com/abisheakp197/Neutral-Trust-Infrastructure at `8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3`, `conformance/witness/README.md` SHA-256 `95d6566512be6387dd72a169cc4ad768356ee2ba7c44c31c97d03ef8e8cab220`). Inputs were admitted by the runner; this is not producer consent, producer admission, review or endorsement.

## Challenge

This run answers a public verification challenge by abisheakp197 (https://github.com/aeoess/agent-governance-vocabulary/issues/177#issuecomment-6706266993). The challenge is context only: it is not consent, not an offer, not admission and not a publication approval. Answering it is not endorsement.

The challenge asked:

- take the public key, the signed RESULTS.json and generate_seals.py
- pull the bytes and recompute the hashes
- try to break the Merkle root
- open an issue if a flaw is found

The challenge also asked for endorsement. This run gives none: an endorsement is a separate statement by a person and lies outside every claim ceiling in this report.

Publication status: see STATUS.md. Agreement: None

## Pinned inputs

| Project | Repository | Commit | Licence |
|---|---|---|---|
| Neutral Trust Infrastructure (NTI) | https://github.com/abisheakp197/Neutral-Trust-Infrastructure | `8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3` | Apache-2.0 |
| Neutral Trust Infrastructure (NTI) | https://github.com/abisheakp197/Neutral-Trust-Infrastructure | `896d352a23d1e8bada5c543fc797e45f8638899d` | Apache-2.0 |

Frozen plan SHA-256: `bb621f086d2b58681ca397273839ea275d8d40aa5c92f2211079457ae9215e60` (Python 3.13.18).

Preregistered: no.

## Claim ceiling

Establishes:

- per-claim results over the pinned bytes of the NTI witness package at commit 8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3
- runner probes over the pinned bytes at that commit and at 896d352a23d1e8bada5c543fc797e45f8638899d, each with a recomputable witness

Does not establish:

- who holds the signing key or that the key is the producer's: it has no external trust anchor
- that the Rust and Python suites passed: RESULTS.json asserts it, the package does not evidence it
- anything about production evidence: the S4/S5/S6 seals cover a synthetic fixture
- the security of NTI code or of any deployment
- endorsement of NTI, of its maintainers or of any application

## Per-claim results

| Input | Claim | Execution | Result | Reads | Unresolved obligations |
|---|---|---|---|---|---|
| witness | package_signature | COMPLETED | ESTABLISHED | RESULTS.json, MANIFEST.json, SIGNATURE.sig, PUBLIC_KEY.pem |  |
| pages | package_signature | COMPLETED | ESTABLISHED | RESULTS.json, MANIFEST.json, SIGNATURE.sig, PUBLIC_KEY.pem |  |
| witness | s6_seal | COMPLETED | ESTABLISHED | RESULTS.json, PUBLIC_KEY.pem |  |
| pages | s6_seal | COMPLETED | ESTABLISHED | RESULTS.json, PUBLIC_KEY.pem |  |
| tree | s4_digests | COMPLETED | ESTABLISHED | conformance/witness/RESULTS.json, conformance/witness_generator/sample_evidence.json |  |
| tree | s5_root | COMPLETED | ESTABLISHED | conformance/witness/RESULTS.json |  |
| tree | manifest_hashes | COMPLETED | ESTABLISHED | conformance/witness/MANIFEST.json, manifest-listed files |  |
| tree | pages_mirror | COMPLETED | ESTABLISHED | conformance/witness/*, docs/witness/* |  |
| tree | suite_outcomes_evidenced | COMPLETED | NOT_ESTABLISHED | conformance/witness/RESULTS.json | a test transcript or CI attestation bound to the pinned commit, an independent rerun of the pinned Rust and Python suites |
| tree | key_anchor | COMPLETED | NOT_ESTABLISHED | conformance/witness/PUBLIC_KEY.pem | publication of the key outside the repository it signs, a key custody and rotation statement |

## Probes (runner findings, not claim results)

Runner-authored probes over the pinned bytes. DEMONSTRATED means the runner's check reproduced the probed property and recorded a deterministic witness; NOT_DEMONSTRATED means it did not. A probe is not a claim result, never maps to PASS or FAIL, and is not a statement by the producer. Assessment levels are the runner's judgment and are never summed or ranked.

| Probe | Class | Runner assessment | Execution | Observation | Affects pinned artifact |
|---|---|---|---|---|---|
| `s5_documented_vs_implemented` | SPEC_IMPLEMENTATION_DIVERGENCE | medium | COMPLETED | DEMONSTRATED | no |
| `s5_leaf_count_binding` | CONSTRUCTION_AMBIGUITY | medium | COMPLETED | DEMONSTRATED | no |
| `s6_message_binding` | BINDING_GAP | medium | COMPLETED | DEMONSTRATED | yes |
| `package_signature_framing` | FRAMING_GAP | low | COMPLETED | DEMONSTRATED | yes |
| `key_reuse_without_context` | KEY_REUSE | informational | COMPLETED | DEMONSTRATED | yes |
| `key_changed_between_revisions` | TRUST_ANCHOR | low | COMPLETED | DEMONSTRATED | yes |
| `s4_s5_s6_meaning_changed` | TERMINOLOGY_CHANGE | informational | COMPLETED | DEMONSTRATED | yes |

### `s5_documented_vs_implemented`

**Probed:** The S5 construction in the published generator and verifier is the construction the README documents.

**Runner assessment (medium):** A witness following the README and one following verify.sh disagree for every package whose leaf count is not a power of two. The published four-leaf package is unaffected.

**Observed:** The README states that an odd node is promoted unchanged; the published generator and verify.sh pair an odd last node with itself. The two rules give different roots for leaf counts 3, 5, 6, 7 and the same root for the published 4-leaf tree.

Inputs: `tree:sha256:08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68`

Witness:

```json
{
  "documented_rule_equals_rfc6962_split_1_to_8": true,
  "generator_rule_line": 106,
  "generator_sha256": "85b0bef27b0dc3a9c4e80fa3f5030f59be4751bbcc28face8a570a2f2f84f02d",
  "leaf_counts_where_roots_differ_1_to_8": [
    3,
    5,
    6,
    7
  ],
  "published_leaf_count": 4,
  "published_root_same_under_both_rules": true,
  "readme_rule_line": 29,
  "readme_sha256": "95d6566512be6387dd72a169cc4ad768356ee2ba7c44c31c97d03ef8e8cab220",
  "vector_leaves": "sha256(b'nti-probe-leaf-<i>') for i = 1..n",
  "vectors": [
    {
      "documented_root": "ac82615f795a97024f7e37260d2631e826cb272fd1ba39d0f39bb4b991fbb387",
      "implemented_root": "f8a508e4553b830073109bea58480629ea2d9ae012d56463d21d5b93a118aa25",
      "n": 3
    },
    {
      "documented_root": "aacea387e9cc630c8af19ffb713113724090480929d0d3c6634a12d16f453c3d",
      "implemented_root": "403cc54b55aa48802489a7509418a796789d7e7c846419cb18ab3841961df97d",
      "n": 5
    },
    {
      "documented_root": "8f8f6b9331f82734991434c896bd684ff7626ca05ca3b9bcf4e8e61ff69d6148",
      "implemented_root": "7007109afd314e560ef7fe63bc46f136749c924e5d15bcd96522a748d0211ee7",
      "n": 6
    },
    {
      "documented_root": "3f68d23c0f63e7b0475be001a4cfdaa950a15d18b4f6199736ead5e3edb40cd0",
      "implemented_root": "e58eedb213c31c19a212d94286795dee70c1cccf1de55e90f07a321c6f34a4a4",
      "n": 7
    }
  ],
  "verifier_rule_line": 46,
  "verifier_sha256": "355e809e679cfa8ba3e25ce64691b6eb5b0e0a547b171e272d1d35750453f324"
}
```

Source locators (read as data, never executed):

- [conformance/witness/README.md L29](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/README.md#L29): documented rule: odd nodes are promoted unchanged
- [conformance/witness_generator/generate_seals.py L96-111](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness_generator/generate_seals.py#L96-L111): generator pairs an odd last node with itself
- [conformance/witness/verify.sh L45-47](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/verify.sh#L45-L47): published verifier uses the same duplicating rule

**Suggested remediation:** Implement the documented rule in generate_seals.py and verify.sh (promote the odd node, which equals the RFC 6962 split), and commit vectors for leaf counts 1, 3, 5, 6 and 7 that both must pass.

### `s5_leaf_count_binding`

**Probed:** Under the implemented S5 rule, distinct leaf lists have distinct roots, so the S6 seal binds the leaf count.

**Runner assessment (medium):** Under the implemented rule two different evidence lists can share one root and one seal; this is the CVE-2012-2459 pattern. It needs an odd leaf count to matter, which the published package does not have.

**Observed:** Under the implemented rule a list of n leaves and the same list with its last leaf repeated have the same root (n = 3, 5, 7), and S6 signs only the 32-byte root, so the seal does not bind the leaf count. The published tree has even sizes at every level, so it is not affected.

Inputs: `tree:sha256:08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68`

Witness:

```json
{
  "leaf_count_inside_s6_message": false,
  "pairs": [
    {
      "collide": true,
      "leaf_count": 3,
      "root": "f8a508e4553b830073109bea58480629ea2d9ae012d56463d21d5b93a118aa25",
      "root_with_repeat": "f8a508e4553b830073109bea58480629ea2d9ae012d56463d21d5b93a118aa25",
      "with_last_leaf_repeated": 4
    },
    {
      "collide": true,
      "leaf_count": 5,
      "root": "403cc54b55aa48802489a7509418a796789d7e7c846419cb18ab3841961df97d",
      "root_with_repeat": "403cc54b55aa48802489a7509418a796789d7e7c846419cb18ab3841961df97d",
      "with_last_leaf_repeated": 6
    },
    {
      "collide": true,
      "leaf_count": 7,
      "root": "e58eedb213c31c19a212d94286795dee70c1cccf1de55e90f07a321c6f34a4a4",
      "root_with_repeat": "e58eedb213c31c19a212d94286795dee70c1cccf1de55e90f07a321c6f34a4a4",
      "with_last_leaf_repeated": 8
    }
  ],
  "published_level_sizes": [
    4,
    2,
    1
  ],
  "published_tree_used_duplication": false,
  "rfc6962_split_collides_on_same_pairs": false,
  "s6_message_bytes": 32,
  "s6_signs": "S5_evidence_root.merkle_root_sha256",
  "vector_leaves": "sha256(b'nti-probe-leaf-<i>') for i = 1..n"
}
```

Source locators (read as data, never executed):

- [conformance/witness_generator/generate_seals.py L106](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness_generator/generate_seals.py#L106): right = level[i] when no right sibling exists

**Suggested remediation:** Fix the odd-node rule as above and put the leaf count inside the signed S6 message.

### `s6_message_binding`

**Probed:** The S6 seal binds the artifact names, byte counts, leaf count and classification it is published with.

**Runner assessment (medium):** The seal is portable: on its own it vouches for a root, not for what the root is said to cover, including the SYNTHETIC classification.

**Observed:** After relabelling the fixture PRODUCTION and renaming an artifact, the S5 root is unchanged and the S6 seal still verifies; only the outer package signature fails. The seal alone can be carried into a context that misdescribes what it covers.

Inputs: `witness:sha256:1ed076b37f8ff6f3676c5eea62394339898f2abe05f1d1ba35425e0fe3804915`

Witness:

```json
{
  "changed": {
    "S4_file_integrity[1].name": [
      "request.json",
      "payment_authorization.json"
    ],
    "seal_scope.classification": [
      "SYNTHETIC - test fixture, not production evidence",
      "PRODUCTION"
    ]
  },
  "fields_bound_by_s6": [
    "S5_evidence_root.merkle_root_sha256"
  ],
  "fields_not_bound_by_s6": [
    "S4 artifact names",
    "S4 byte counts",
    "S5 leaf_count",
    "seal_scope.classification",
    "scope",
    "suites"
  ],
  "package_signature_verifies_after_relabel": false,
  "relabelled_results_sha256": "0cc7743cce0d1886a6e0e0cce487b3f58a4e412139d8b1a3e40a1cd61648029b",
  "s5_root_after_relabel": "20271a5928932d6362ff566207e20f60cb2a5e387a7178dbf6da028d7c01fe1e",
  "s6_seal_verifies_after_relabel": true
}
```

Source locators (read as data, never executed):

- [conformance/witness_generator/generate_seals.py L142-147](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness_generator/generate_seals.py#L142-L147): S6 signs bytes.fromhex(root_hex) only

**Suggested remediation:** Sign a domain-tagged structured S6 message, for example nti-s6-v1: || root || u32(leaf_count) || sha256(evidence_package) || classification, and hash name || content into each S4 leaf.

### `package_signature_framing`

**Probed:** The package signature authenticates where RESULTS.json ends and MANIFEST.json begins.

**Runner assessment (low):** With strict JSON parsers only whitespace can move between the files; lenient multi-document parsers widen it.

**Observed:** Moving the final newline of RESULTS.json to the start of MANIFEST.json gives two different files, both strict JSON, that verify under the same signature. The boundary between the signed files is not authenticated; with strict parsers only whitespace can move.

Inputs: `witness:sha256:1ed076b37f8ff6f3676c5eea62394339898f2abe05f1d1ba35425e0fe3804915`

Witness:

```json
{
  "both_shifted_files_are_strict_json": true,
  "manifest_sha256": "b29af6001024d919d33ea18d414cbcb303d70eada68d21cd17947267ee373cd4",
  "results_sha256": "2c9ff6a8850d9a4069855a664a7671a5c02f4e4441726025c13b3189359fd7a5",
  "shifted_manifest_sha256": "b3ddff6a4ae9ca7bf01d545b17483aa9ab7a32c7ee0364a15e8477457f0f3731",
  "shifted_results_sha256": "702697138872edbb40205d5ae55c26c442027a62370d994a103c85483cfbc9ae",
  "signature_verifies_on_shifted_pair": true,
  "signed_message": "RESULTS.json || MANIFEST.json, no length prefix or separator"
}
```

Source locators (read as data, never executed):

- [conformance/witness/sign.sh L11](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/sign.sh#L11): signed message is cat RESULTS.json MANIFEST.json

**Suggested remediation:** Sign a length-prefixed concatenation, or a canonical list of (file name, SHA-256) pairs.

### `key_reuse_without_context`

**Probed:** The S6 seal and the package signature are separated by key or by a context string.

**Runner assessment (informational):** No cross-use is exploitable in the published package; it is a design hazard for future messages.

**Observed:** One Ed25519 key signs both the package and the S6 seal, and the S6 message is the bare 32-byte root with no context string, so any 32-byte value this key ever signs reads as a valid S6 seal.

Inputs: `witness:sha256:1ed076b37f8ff6f3676c5eea62394339898f2abe05f1d1ba35425e0fe3804915`

Witness:

```json
{
  "package_signature_message_bytes": 8293,
  "public_key_raw_hex": "ababaf03f4bee7900ae3a91050a3de723c7b302f4020b465f0c0466222f50906",
  "s6_message_bytes": 32,
  "s6_message_has_context_prefix": false,
  "s6_message_hex": "20271a5928932d6362ff566207e20f60cb2a5e387a7178dbf6da028d7c01fe1e",
  "same_key_verifies_both": true
}
```

**Suggested remediation:** Use a separate key for S6, or prefix every signed message with a context string such as nti-s6-v1: and nti-package-v1:.

### `key_changed_between_revisions`

**Probed:** The witness key is stable across the published revisions, or its change is recorded in the package.

**Runner assessment (low):** The README already says the key has no external anchor; the change shows why that matters for a witness relationship.

**Observed:** The witness key differs between the two pinned revisions and each package verifies under its own key. Nothing in the pinned package records the change, so a verifier holding only the repository cannot tell which key is authoritative.

Inputs: `witness:sha256:1ed076b37f8ff6f3676c5eea62394339898f2abe05f1d1ba35425e0fe3804915`, `history_witness:sha256:428ee644a679a8cd480a43b79472fa3471ff8bfb14bc501a17c78bb91fb4452c`

Witness:

```json
{
  "earlier_key_pem_sha256": "66003123efc80e3eb1d849fc0680732567560570c785edfbbe3960574bb1c64f",
  "earlier_key_raw_hex": "02815770232bae5e72b61ad17b675a21b3846d1bd1a0fc58e64ae8ea98d3808f",
  "earlier_package_verifies_under_earlier_key": true,
  "pinned_key_pem_sha256": "4153ddbbf43f5576a53515b18934a0b5fdc088c62250d709f6c4594e41016075",
  "pinned_key_raw_hex": "ababaf03f4bee7900ae3a91050a3de723c7b302f4020b465f0c0466222f50906",
  "pinned_package_verifies_under_pinned_key": true,
  "pinned_readme_mentions_rotation": false
}
```

**Suggested remediation:** Publish the key outside the repository (signed tag, DID document or keyserver) with a custody note, and record rotations in the package.

### `s4_s5_s6_meaning_changed`

**Probed:** The identifiers S4, S5 and S6 keep the meaning they had in the earlier published revision, or the pinned package records the change.

**Runner assessment (informational):** Not a cryptographic issue. A reader comparing the two public revisions could take S4/S5/S6 results for one meaning as covering the other; nothing here bears on where the construction or its code came from.

**Observed:** In the earlier revision, S4, S5 and S6 denote invariants of the separate ASL project (S4 a threshold and tripwire property, S5 a kill-path cascade, S6 undefined), recorded there as not run. In the pinned revision the same identifiers denote a seal construction (artifact digests, a Merkle root, an Ed25519 signature). The pinned package does not record this change of meaning, and it refers to a witness specification for the field names without identifying it. This concerns terminology only; it says nothing about where the construction or any code came from.

Inputs: `witness:sha256:1ed076b37f8ff6f3676c5eea62394339898f2abe05f1d1ba35425e0fe3804915`, `history_witness:sha256:428ee644a679a8cd480a43b79472fa3471ff8bfb14bc501a17c78bb91fb4452c`

Witness:

```json
{
  "earlier_meaning": {
    "S4": "Thresholds are quiet on ordinary traffic, but the tripwire still fires.",
    "S5": "Every kill path still fires the complete cascade.",
    "S6": "Not defined in the public ASL conformance kit revision."
  },
  "earlier_record_sha256": "480a0a512839d14fae77b320d9caa06f057e4b63425796b53baabaecb2ee4bf9",
  "earlier_status_in_results": {
    "S4": "NOT_RUN",
    "S5": "NOT_RUN",
    "S6": "NOT_RUN"
  },
  "pinned_meaning": {
    "S4": "S4 file integrity: SHA-256 of each evidence artifact, in declared order.",
    "S5": "S5 evidence root: Merkle root over the S4 digests. SHA-256, RFC-6962-style, with leaf/node domain separation (`nti-s5-leaf-v1:`, `nti-s5-node-v1:`). Odd nodes are promoted unchanged.",
    "S6": "S6 seal: Ed25519 signature over the S5 root."
  },
  "pinned_package_mentions_earlier_meaning": false,
  "pinned_readme_links_that_specification": false,
  "pinned_readme_refers_to_a_witness_specification": true,
  "pinned_readme_sha256": "95d6566512be6387dd72a169cc4ad768356ee2ba7c44c31c97d03ef8e8cab220"
}
```

Source locators (read as data, never executed):

- [conformance/witness/README.md L25-31](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/README.md#L25-L31): pinned meaning: the S4/S5/S6 seal table
- [conformance/witness/README.md L32-33](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/README.md#L32-L33): refers to a witness specification for the field name without identifying it
- [conformance/witness/vendor/S4_S5_S6_PROVENANCE.md L11-21](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/896d352a23d1e8bada5c543fc797e45f8638899d/conformance/witness/vendor/S4_S5_S6_PROVENANCE.md#L11-L21): earlier meaning: ASL invariants S4 and S5, S6 undefined

**Suggested remediation:** State in the README that S4/S5/S6 now name the seal construction rather than the ASL invariants named by the earlier revision, and identify the witness specification the field names follow.

## Per-claim ceilings

`package_signature` establishes:

- RESULTS.json || MANIFEST.json verifies under PUBLIC_KEY.pem (RFC 8032, canonical S), and a one-byte change or reversed order does not

`package_signature` does not establish:

- who holds the key

## Independence per claim

Runner-authored material: verifier/nti_witness.py, claims suite_outcomes_evidenced and key_anchor, every probe.

| Claim | Independent | Basis |
|---|---|---|
| package_signature | no | run label SECOND_IMPLEMENTATION |
| s6_seal | no | run label SECOND_IMPLEMENTATION |
| s4_digests | no | run label SECOND_IMPLEMENTATION |
| s5_root | no | run label SECOND_IMPLEMENTATION |
| manifest_hashes | no | run label SECOND_IMPLEMENTATION |
| pages_mirror | no | run label SECOND_IMPLEMENTATION |
| suite_outcomes_evidenced | no | run label SECOND_IMPLEMENTATION |
| key_anchor | no | run label SECOND_IMPLEMENTATION |

## Limits

- Verification is not endorsement, adoption, dependency or transfer of ownership.
- A survivor means this corpus did not distinguish that fault on the declared projection; it is not a checker defect.
- Crash kills are listed separately and are not projection changes.
- Nothing is summed across rows, fault sets or claims, and there is no percentage headline.
- Local execution is not network isolation.
- Until STATUS.md says PUBLISHED, this report is not citable as public evidence.

Prepared with the Agent Authority Conformance lab; see CONSENT.json for who agreed to what.
