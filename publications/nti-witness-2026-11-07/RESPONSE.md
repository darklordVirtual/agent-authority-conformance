## Bounded verification: `nti-witness`

Answering the public verification challenge by abisheakp197 (https://github.com/aeoess/agent-governance-vocabulary/issues/177#issuecomment-6706266993). The challenge asked to:

- take the public key, the signed RESULTS.json and generate_seals.py
- pull the bytes and recompute the hashes
- try to break the Merkle root
- open an issue if a flaw is found

**Status:** Lab state `PACKAGED`: not yet published through the lab. Every value below is recomputable from the pinned bytes, but the run package is not citable as published evidence until its STATUS.md says PUBLISHED.

### Method

- **Independence:** SECOND_IMPLEMENTATION. A reproduction made with knowledge of the producer's code; not independent verification. Reads as `SECOND_IMPLEMENTATION`, BCR-2 at most.
- **Independence statement:** The checks in verifier/nti_witness.py were written by the runner from the pinned README, after reading the producer's verify.sh and generate_seals.py; no producer code is imported or executed and Ed25519 is the runner's own RFC 8032 implementation. Because the producer's code was read first, this is labelled SECOND_IMPLEMENTATION, not INDEPENDENT_IMPLEMENTATION.
- **Track:** self-service over a pinned public boundary (https://github.com/abisheakp197/Neutral-Trust-Infrastructure at `8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3`, `conformance/witness/README.md` SHA-256 `95d6566512be6387dd72a169cc4ad768356ee2ba7c44c31c97d03ef8e8cab220`). Inputs were admitted by the runner; this is not producer consent, producer admission, review or endorsement.
- **Procedure:** `nti-witness-readme-how-to-verify: the README steps, run with the runner's own checks`.
- **Frozen plan SHA-256:** `bb621f086d2b58681ca397273839ea275d8d40aa5c92f2211079457ae9215e60`; not preregistered (frozen and run without publishing the hash first).
- **Checks:** the lab loads only the runner's own modules below (hashes from the frozen plan) and hands them the pinned subject files as data, as bytes or parsed JSON per input.
  - `verifier/nti_witness.py` `04a48bd332a28d86bd735de611ac50dd6e0143293de536260cb3e94724a8cca6`
- **Lab:** run executed with AACP commit `dfa4277723d78f432d9349d64bcb8b16f325dea3` (from RUN-CAPTURE.json); Python 3.13.18.
- **Trust material:** PUBLIC_KEY.pem as committed at each pinned commit. It has no external trust anchor, so a valid signature establishes integrity under that key, not who holds it.
- **Who:** checks by darklordVirtual; run operated by Agent Authority Conformance.

### Claim results

One row per (input, claim). `ESTABLISHED`, `CONTRADICTED` and `NOT_ESTABLISHED` are bounded by the claim ceiling below; anything else is a non-verdict.

| Claim | Input | Input digest | Result | Unresolved obligations |
|---|---|---|---|---|
| `package_signature` | `witness` | `1ed076b37f8ff6f3676c5eea62394339898f2abe05f1d1ba35425e0fe3804915` | **ESTABLISHED** | — |
| `package_signature` | `pages` | `439dbfe4773f853fa8e745c5f4e16d2facfcdb2a31d9f04cacd00b069fc42466` | **ESTABLISHED** | — |
| `s6_seal` | `witness` | `1ed076b37f8ff6f3676c5eea62394339898f2abe05f1d1ba35425e0fe3804915` | **ESTABLISHED** | — |
| `s6_seal` | `pages` | `439dbfe4773f853fa8e745c5f4e16d2facfcdb2a31d9f04cacd00b069fc42466` | **ESTABLISHED** | — |
| `s4_digests` | `tree` | `08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68` | **ESTABLISHED** | — |
| `s5_root` | `tree` | `08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68` | **ESTABLISHED** | — |
| `manifest_hashes` | `tree` | `08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68` | **ESTABLISHED** | — |
| `pages_mirror` | `tree` | `08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68` | **ESTABLISHED** | — |
| `suite_outcomes_evidenced` | `tree` | `08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68` | **NOT_ESTABLISHED** | a test transcript or CI attestation bound to the pinned commit, an independent rerun of the pinned Rust and Python suites |
| `key_anchor` | `tree` | `08ca720d720200445bb778b19a3261cd94ab65cbd8fece9387ec27916dcb0f68` | **NOT_ESTABLISHED** | publication of the key outside the repository it signs, a key custody and rotation statement |

Claims:

- `package_signature`: The Ed25519 signature in SIGNATURE.sig verifies over the raw bytes of RESULTS.json followed by MANIFEST.json under PUBLIC_KEY.pem.
- `s6_seal`: The S6 seal verifies as an Ed25519 signature over the raw 32-byte S5 root under PUBLIC_KEY.pem.
- `s4_digests`: Every S4 entry (name, SHA-256, byte count) recomputes from the pinned evidence fixture, in declared order.
- `s5_root`: The S5 root, leaf count and every published level recompute from the S4 digests under the documented rule (nti-s5-leaf-v1: and nti-s5-node-v1: prefixes, odd node promoted).
- `manifest_hashes`: Every file listed in MANIFEST.json is pinned and has the listed SHA-256.
- `pages_mirror`: The GitHub Pages source docs/witness carries byte-identical copies of the signed package files and of every file it shares with conformance/witness.
- `suite_outcomes_evidenced`: The suite outcomes in RESULTS.json (33 Rust and 2 Python tests passed) are evidenced by material in the pinned package beyond the producer's signature.
- `key_anchor`: The Ed25519 key that signs the package is anchored outside the repository whose content it signs.

### Findings

Runner-authored probes. A finding is the runner's reproducible observation with a witness anyone can recompute; it is not a claim result and not a statement by the producer. Assessment levels are the runner's judgment and are not summed.

#### Holding for the pinned bytes as published

**F1. `s6_message_binding`** · BINDING_GAP · runner assessment: medium · DEMONSTRATED · affects the pinned artifact: yes

*Probed:* The S6 seal binds the artifact names, byte counts, leaf count and classification it is published with.

*Observed:* After relabelling the fixture PRODUCTION and renaming an artifact, the S5 root is unchanged and the S6 seal still verifies; only the outer package signature fails. The seal alone can be carried into a context that misdescribes what it covers.

*Why this level:* The seal is portable: on its own it vouches for a root, not for what the root is said to cover, including the SYNTHETIC classification.

*Where (read as data, not executed):*

- [conformance/witness_generator/generate_seals.py L142-147](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness_generator/generate_seals.py#L142-L147): S6 signs bytes.fromhex(root_hex) only

<details><summary>Witness</summary>

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

</details>

*Suggested fix:* Sign a domain-tagged structured S6 message, for example nti-s6-v1: || root || u32(leaf_count) || sha256(evidence_package) || classification, and hash name || content into each S4 leaf.

**F2. `package_signature_framing`** · FRAMING_GAP · runner assessment: low · DEMONSTRATED · affects the pinned artifact: yes

*Probed:* The package signature authenticates where RESULTS.json ends and MANIFEST.json begins.

*Observed:* Moving the final newline of RESULTS.json to the start of MANIFEST.json gives two different files, both strict JSON, that verify under the same signature. The boundary between the signed files is not authenticated; with strict parsers only whitespace can move.

*Why this level:* With strict JSON parsers only whitespace can move between the files; lenient multi-document parsers widen it.

*Where (read as data, not executed):*

- [conformance/witness/sign.sh L11](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/sign.sh#L11): signed message is cat RESULTS.json MANIFEST.json

<details><summary>Witness</summary>

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

</details>

*Suggested fix:* Sign a length-prefixed concatenation, or a canonical list of (file name, SHA-256) pairs.

**F3. `key_reuse_without_context`** · KEY_REUSE · runner assessment: informational · DEMONSTRATED · affects the pinned artifact: yes

*Probed:* The S6 seal and the package signature are separated by key or by a context string.

*Observed:* One Ed25519 key signs both the package and the S6 seal, and the S6 message is the bare 32-byte root with no context string, so any 32-byte value this key ever signs reads as a valid S6 seal.

*Why this level:* No cross-use is exploitable in the published package; it is a design hazard for future messages.

<details><summary>Witness</summary>

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

</details>

*Suggested fix:* Use a separate key for S6, or prefix every signed message with a context string such as nti-s6-v1: and nti-package-v1:.

**F4. `key_changed_between_revisions`** · TRUST_ANCHOR · runner assessment: low · DEMONSTRATED · affects the pinned artifact: yes

*Probed:* The witness key is stable across the published revisions, or its change is recorded in the package.

*Observed:* The witness key differs between the two pinned revisions and each package verifies under its own key. Nothing in the pinned package records the change, so a verifier holding only the repository cannot tell which key is authoritative.

*Why this level:* The README already says the key has no external anchor; the change shows why that matters for a witness relationship.

<details><summary>Witness</summary>

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

</details>

*Suggested fix:* Publish the key outside the repository (signed tag, DID document or keyserver) with a custody note, and record rotations in the package.

**F5. `s4_s5_s6_meaning_changed`** · TERMINOLOGY_CHANGE · runner assessment: informational · DEMONSTRATED · affects the pinned artifact: yes

*Probed:* The identifiers S4, S5 and S6 keep the meaning they had in the earlier published revision, or the pinned package records the change.

*Observed:* In the earlier revision, S4, S5 and S6 denote invariants of the separate ASL project (S4 a threshold and tripwire property, S5 a kill-path cascade, S6 undefined), recorded there as not run. In the pinned revision the same identifiers denote a seal construction (artifact digests, a Merkle root, an Ed25519 signature). The pinned package does not record this change of meaning, and it refers to a witness specification for the field names without identifying it. This concerns terminology only; it says nothing about where the construction or any code came from.

*Why this level:* Not a cryptographic issue. A reader comparing the two public revisions could take S4/S5/S6 results for one meaning as covering the other; nothing here bears on where the construction or its code came from.

*Where (read as data, not executed):*

- [conformance/witness/README.md L25-31](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/README.md#L25-L31): pinned meaning: the S4/S5/S6 seal table
- [conformance/witness/README.md L32-33](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/README.md#L32-L33): refers to a witness specification for the field name without identifying it
- [conformance/witness/vendor/S4_S5_S6_PROVENANCE.md L11-21](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/896d352a23d1e8bada5c543fc797e45f8638899d/conformance/witness/vendor/S4_S5_S6_PROVENANCE.md#L11-L21): earlier meaning: ASL invariants S4 and S5, S6 undefined

<details><summary>Witness</summary>

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

</details>

*Suggested fix:* State in the README that S4/S5/S6 now name the seal construction rather than the ASL invariants named by the earlier revision, and identify the witness specification the field names follow.

#### Shown only on constructed inputs: the pinned bytes are not affected, and no attack on the published package is demonstrated

**F6. `s5_documented_vs_implemented`** · SPEC_IMPLEMENTATION_DIVERGENCE · runner assessment: medium · DEMONSTRATED · affects the pinned artifact: no

*Probed:* The S5 construction in the published generator and verifier is the construction the README documents.

*Observed:* The README states that an odd node is promoted unchanged; the published generator and verify.sh pair an odd last node with itself. The two rules give different roots for leaf counts 3, 5, 6, 7 and the same root for the published 4-leaf tree.

*Why this level:* A witness following the README and one following verify.sh disagree for every package whose leaf count is not a power of two. The published four-leaf package is unaffected.

*Where (read as data, not executed):*

- [conformance/witness/README.md L29](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/README.md#L29): documented rule: odd nodes are promoted unchanged
- [conformance/witness_generator/generate_seals.py L96-111](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness_generator/generate_seals.py#L96-L111): generator pairs an odd last node with itself
- [conformance/witness/verify.sh L45-47](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness/verify.sh#L45-L47): published verifier uses the same duplicating rule

<details><summary>Witness</summary>

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

</details>

*Suggested fix:* Implement the documented rule in generate_seals.py and verify.sh (promote the odd node, which equals the RFC 6962 split), and commit vectors for leaf counts 1, 3, 5, 6 and 7 that both must pass.

**F7. `s5_leaf_count_binding`** · CONSTRUCTION_AMBIGUITY · runner assessment: medium · DEMONSTRATED · affects the pinned artifact: no

*Probed:* Under the implemented S5 rule, distinct leaf lists have distinct roots, so the S6 seal binds the leaf count.

*Observed:* Under the implemented rule a list of n leaves and the same list with its last leaf repeated have the same root (n = 3, 5, 7), and S6 signs only the 32-byte root, so the seal does not bind the leaf count. The published tree has even sizes at every level, so it is not affected.

*Why this level:* Under the implemented rule two different evidence lists can share one root and one seal; this is the CVE-2012-2459 pattern. It needs an odd leaf count to matter, which the published package does not have.

*Where (read as data, not executed):*

- [conformance/witness_generator/generate_seals.py L106](https://github.com/abisheakp197/Neutral-Trust-Infrastructure/blob/8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3/conformance/witness_generator/generate_seals.py#L106): right = level[i] when no right sibling exists

<details><summary>Witness</summary>

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

</details>

*Suggested fix:* Fix the odd-node rule as above and put the leaf count inside the signed S6 message.

### What this does and does not establish

Establishes:

- per-claim results over the pinned bytes of the NTI witness package at commit 8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3
- runner probes over the pinned bytes at that commit and at 896d352a23d1e8bada5c543fc797e45f8638899d, each with a recomputable witness

Does not establish:

- who holds the signing key or that the key is the producer's: it has no external trust anchor
- that the Rust and Python suites passed: RESULTS.json asserts it, the package does not evidence it
- anything about production evidence: the S4/S5/S6 seals cover a synthetic fixture
- the security of NTI code or of any deployment
- endorsement of NTI, of its maintainers or of any application

### Endorsement

The challenge asked for endorsement if the claims hold. This response gives none. A verified artifact is not an endorsed project, and endorsement is outside every claim ceiling above.

### Pinned bytes

| Subject | Repository | Commit | Files pinned |
|---|---|---|---|
| 0 | https://github.com/abisheakp197/Neutral-Trust-Infrastructure | `8ca84887317d6d7e3cb52d1cad4e639b07f1d8d3` | 30 |
| 1 | https://github.com/abisheakp197/Neutral-Trust-Infrastructure | `896d352a23d1e8bada5c543fc797e45f8638899d` | 11 |

<details><summary>Subject 0: SHA-256 of every pinned file</summary>

| File | SHA-256 |
|---|---|
| `.github/workflows/issuer-quorum-regressions.yml` | `87975c4ad9a0fa4b753b419a25c3a3d49c4e723d328ff4e014fb0f147b827730` |
| `conformance/witness/.gitignore` | `b4ef5aaab1e8843af76582bf0811569f39c23595731d237229e56e1f66592493` |
| `conformance/witness/MANIFEST.json` | `b29af6001024d919d33ea18d414cbcb303d70eada68d21cd17947267ee373cd4` |
| `conformance/witness/PUBLIC_KEY.pem` | `4153ddbbf43f5576a53515b18934a0b5fdc088c62250d709f6c4594e41016075` |
| `conformance/witness/README.md` | `95d6566512be6387dd72a169cc4ad768356ee2ba7c44c31c97d03ef8e8cab220` |
| `conformance/witness/RESULTS.json` | `2c9ff6a8850d9a4069855a664a7671a5c02f4e4441726025c13b3189359fd7a5` |
| `conformance/witness/SIGNATURE.sig` | `c18566b6bb37fbdd6733da9777fe66789c22034ab9f959a8e670a1866940e162` |
| `conformance/witness/sign.sh` | `7bdde5dbb4ab0b36880cca42d9eb99b4e743d995c9dfb9933ab6808bf319985e` |
| `conformance/witness/verify.sh` | `355e809e679cfa8ba3e25ce64691b6eb5b0e0a547b171e272d1d35750453f324` |
| `conformance/witness_generator/generate_seals.py` | `85b0bef27b0dc3a9c4e80fa3f5030f59be4751bbcc28face8a570a2f2f84f02d` |
| `conformance/witness_generator/sample_evidence.json` | `d988746568821931152a6567d9929b7052abf692a319f340d47688ae5350cc84` |
| `docs/witness/MANIFEST.json` | `b29af6001024d919d33ea18d414cbcb303d70eada68d21cd17947267ee373cd4` |
| `docs/witness/PUBLIC_KEY.pem` | `4153ddbbf43f5576a53515b18934a0b5fdc088c62250d709f6c4594e41016075` |
| `docs/witness/README.md` | `95d6566512be6387dd72a169cc4ad768356ee2ba7c44c31c97d03ef8e8cab220` |
| `docs/witness/RESULTS.json` | `2c9ff6a8850d9a4069855a664a7671a5c02f4e4441726025c13b3189359fd7a5` |
| `docs/witness/SIGNATURE.sig` | `c18566b6bb37fbdd6733da9777fe66789c22034ab9f959a8e670a1866940e162` |
| `docs/witness/index.html` | `11e065664808dcb2cb3b0bedf7027733774418475cb21f74b1f610ebd25a825b` |
| `docs/witness/sign.sh` | `7bdde5dbb4ab0b36880cca42d9eb99b4e743d995c9dfb9933ab6808bf319985e` |
| `docs/witness/verify.sh` | `355e809e679cfa8ba3e25ce64691b6eb5b0e0a547b171e272d1d35750453f324` |
| `ube-foundation/Cargo.lock` | `3fe85cec7e96773c65a3d37c7640e8a69a5202dc2e0f95fe532661f12613833e` |
| `ube-foundation/Cargo.toml` | `11a42eba316fa3e9a8a85e66dff3cdc492c4a6bb2cc3d947b7d36ec34f87fc28` |
| `ube-foundation/python_tests/test_python_sdk.py` | `0c88b846b62cd69de2ab3c6c382ca2c7cdb6f5cdab3a2cbe2d622330b0495093` |
| `ube-foundation/tests/adversarial_fuzz.rs` | `325f4aca981b2c93f3c3d974add6953736be2313d95495da9e20c2758ccd14e8` |
| `ube-foundation/tests/adversarial_suite.rs` | `d4536b2c7c00313b67c219e2ce92c80a87c035c51da91cf557e360012231ebdd` |
| `ube-foundation/tests/core_tests.rs` | `e13a23e324262fcb65429767dbb519e833714d62a4509d5523d9e2f72e66ab61` |
| `ube-foundation/tests/enterprise_adversarial_stress_suite.rs` | `c107e7fa629f630663ff20b8d0aeb60c41cc56c8ad05648cc7db3eaefd6cb584` |
| `ube-foundation/tests/nti_conformance_regressions.rs` | `ff6b3e8bdf88d750f186f4e6a57afd7ec0da891cb002c5dccab197fc51becb7e` |
| `ube-foundation/tests/robustness_fuzz.rs` | `184c6847fbd418bd9f172231d7124ccc67cdcf2cb52e037b6314db95b1e5438d` |
| `ube-foundation/tests/security_patch_tests.rs` | `52df5a6bc84aa34c0df7036c6a418987f7a61a23d17656c9d302d1fb4967284e` |
| `ube-foundation/tests/trust_marketplace_adversarial.rs` | `846b51a6ff8645f30e6ff6df3075304e95dd9afd34f831a4711d19351907e03d` |

</details>

<details><summary>Subject 1: SHA-256 of every pinned file</summary>

| File | SHA-256 |
|---|---|
| `conformance/witness/.gitignore` | `b4ef5aaab1e8843af76582bf0811569f39c23595731d237229e56e1f66592493` |
| `conformance/witness/MANIFEST.json` | `5dbf032e4177992d03525da191951074fd563a3a9bf95865b3512e8da602ff3f` |
| `conformance/witness/PUBLIC_KEY.pem` | `66003123efc80e3eb1d849fc0680732567560570c785edfbbe3960574bb1c64f` |
| `conformance/witness/README.md` | `99cf0d19cc981701f0f0bde65b3f791d35875dfe3110d5d6088f1ee7d6e18cea` |
| `conformance/witness/RESULTS.json` | `db83ba3464c0507b4eec6fd96c35d77ac8d540a519f0effe4e51ae43743a1931` |
| `conformance/witness/SIGNATURE.sig` | `0d3a5580ceff27a918b69b728acab63b65a61124ce97e6f196966bf03742b13f` |
| `conformance/witness/build_witness.py` | `f56e3867c475dd57179b79473ea11ba05715ba76df4650486d694b246d2adab6` |
| `conformance/witness/sign.sh` | `05768411eab5ad792bd6e7aea79aae4069e756a826513c3d824950b696a42f3a` |
| `conformance/witness/vendor/S4_S5_S6_PROVENANCE.md` | `087e5992679ab905f0d032fcb87676fd69afd26ec67aa8872aa9f3309031eecb` |
| `conformance/witness/vendor/S4_S5_S6_RECORD.json` | `480a0a512839d14fae77b320d9caa06f057e4b63425796b53baabaecb2ee4bf9` |
| `conformance/witness/verify.sh` | `9d428f2639de6efe036d845399abd0af6a226c6d6839f8b24cbca8452eab4ea7` |

</details>

### Reproduce

In the run package, `python3 rerun.py` fetches each subject at its pinned commit, verifies every pinned file hash, recomputes the frozen plan hash and reruns every claim and probe with the vendored lab code (exit 0 `REPRODUCED`, 1 `DIVERGED`, 2 `NOT_REPRODUCIBLE`).

From an AACP checkout, the same run can be operated from its scope:

```sh
python -m conformance.lab init nti-witness-rerun --template templates/runs/nti-witness/SCOPE.json
python -m conformance.lab pin nti-witness-rerun
python -m conformance.lab freeze nti-witness-rerun --not-preregistered
python -m conformance.lab run nti-witness-rerun
```

---

Drafted by agent:claude-opus-5.5; AI-assisted: yes. Prepared with Agent Authority Conformance Profiles (AACP) run protocol v0.3; not a certification, ranking or score.
