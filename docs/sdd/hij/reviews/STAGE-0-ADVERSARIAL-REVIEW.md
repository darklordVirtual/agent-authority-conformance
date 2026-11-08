# Stage 0 adversarial review of SDD-AACP-HIJ-001

**Reviewed:** `docs/sdd/SDD-AACP-HIJ-001.md`, SHA-256 `9b7c8d8f5ec60654df9117fc6e7a3b33cc123a844c49f4c8e7955a5e383b1cc4`
**Against:** CHARTER.md, METHOD.md, GOVERNANCE.md, TERMINOLOGY.md, SPECIFICATION-v0.2.md and
`profiles/AACP-OBSERVED-EFFECT-VANTAGE-1.md` at `main@30a5982`
**Reviewer:** agent `claude-opus-5.5`, AI-drafted. **This review is not independent.** The same agent
drafted the ADRs and wrote the PR #24 lab changes the proposal refers to. The maintainer waived the separate-reviewer requirement for Stage 0 on 2026-11-07;
this remains a disclosed non-independent AI-drafted review, and Gate 0 still requires
recorded dispositions and decisions for every remaining open blocking item.

**Process decision (2026-11-07):** The maintainer explicitly waived the additional independent-reviewer prerequisite for this Stage 0 only. The existing AI-authorship and lack of independence remain disclosed; this is not an assertion of independent verification. Review findings B-01 through B-04 and B-06 remain OPEN. See ADR-0004 and CHECKLIST.md.

Severity: **BLOCKING** must have a maintainer disposition before Stage 1. **SHOULD** must be
addressed in the stage it affects. **NOTE** is for the record. All items are OPEN until the
maintainer records a disposition in the last column.

## Findings

| ID | Severity | Finding | Evidence | Proposed disposition | Maintainer |
|---|---|---|---|---|---|
| B-01 | BLOCKING | The identifiers H, I and J sit in the A–G property namespace. Read with A–G they suggest properties eight to ten and make "A–J" or "10/10" summaries possible, which the proposal's decision 2 forbids. | TERMINOLOGY.md profile identity `AACP-<PROPERTY-NAME>-<revision>`; v0.2 §1 "does not add an eighth property"; CHARTER principle 6 | ADR-0001: descriptive identifiers; letters refused by the validator | OPEN |
| B-02 | BLOCKING | The proposal adds a second new record type, `aacp-profile-assessment-v0.1`, while METHOD.md already plans `bcr-run-v1` as the one new record type. | METHOD.md "Result vocabulary" | ADR-0002: use `bcr-run-v1`, or a tested mapping to it | OPEN |
| B-03 | BLOCKING | The record has three result layers (execution, conclusion, assessment) with no closed table of allowed combinations. METHOD's `NOT_APPLICABLE` and `INCOMPATIBLE` are missing; `UNTESTED` and `NOT_RUN` overlap. The illustrative record (`NOT_ESTABLISHED`, `evidence: []`) is admissible only with a named obligation. | proposal §2.2; v0.2 §2 table | ADR-0003 combination table | OPEN |
| B-04 | BLOCKING | "I vs A–C" claims distinctness from A, but every counterexample runs one way: I holds while A fails. A failed authenticity check also prevents A from passing, so I is a prerequisite of A's authenticity component, not independent of A. Calling it independent overstates separability. | proposal §1.1; TERMINOLOGY A definition "authentic, unmodified, valid and correctly replay-bounded" | ADR-0001: declare a one-way prerequisite relationship, as the vantage profile does for G | OPEN |
| B-05 | BLOCKING | One J profile with six mandatory, separately reported classes is either an implicit aggregate over unrelated claims or six profiles under one name. The proposal names the risk (§9) but defaults to the umbrella. | proposal §5, §9 | ADR-0004: family of class profiles plus an observation prerequisite | **ACCEPTED 2026-11-07**: ADR-0004 option 2 (J1–J5 boundary profiles + J6 observation prerequisite). No aggregate J result. |
| B-06 | BLOCKING | The reference engine is a pure function over admitted evidence (§6), yet H2 asks for atomicity and the J classes for absence of crossings. An observed history cannot prove either for unexercised schedules or undetected events. As written, a PASS would overclaim. | proposal §3 H2, §5 J6, §6 | Ceilings limited to observed histories and to intervals with a detected positive control (DRAFT-CLAIMS); RQ-01, RQ-07 | OPEN |
| S-01 | SHOULD | `profile_version: "1.0.0-draft"` conflicts with integer revisions frozen on merge. | GOVERNANCE.md "A profile revision is frozen when merged" | ADR-0002 | OPEN |
| S-02 | SHOULD | Proposed layout (single-file profiles, `vectors/profiles/`) differs from GOVERNANCE.md's `profiles/<name>/v<n>/` with six parts and `CLAIM_CEILING.md`. The two existing profiles also differ from it. | GOVERNANCE.md "Proposing a profile" | ADR-0002 for new profiles; existing ones untouched | OPEN |
| S-03 | SHOULD | `independence.bcr_level` is self-declared. A validator can at least refuse levels inconsistent with the declared roles. | METHOD.md levels table | ADR-0003 SA-4.3 | OPEN |
| S-04 | SHOULD | I6 says "do not ship home-made production crypto" and "prefer vetted libraries"; the lab vendors standard-library-only code into run packages; the PR #24 NTI example uses a pure-Python, verification-only RFC 8032 implementation. These need one decision. | proposal §4 I6; RUN-PROTOCOL-v0.3 §6 (vendored lab); PR #24 | RQ-05; decide before Stage 3 | OPEN |
| S-05 | SHOULD | The critical discriminator mixes an escalation threshold and a hard limit without a starting balance, window or inclusivity, so two readers can build different vectors from it. | proposal §3 "Critical discriminator" | Exact integer form in DRAFT-CLAIMS §1, for review | OPEN |
| S-06 | SHOULD | `CONTRADICTED` "is not a product-level FAIL without admissibility review", but the proposal does not say what that review records or who performs it. | proposal §2.2 | ADR-0003: an admission record precedes any FAIL transcription; content to be specified in Stage 1 | OPEN |
| S-07 | SHOULD | Synthetic canaries in realistic credential formats can trigger secret scanners and be mistaken for leaks by third parties. | proposal §5 safety conditions | Obviously fake canary format (DRAFT-CLAIMS §3) | OPEN |
| S-08 | SHOULD | Stage 5 requires one non-REMORA implementation per applicable profile, and none is identified. Without one, every profile stays REMORA-only evidence, which CHARTER principle 1 makes weak. | proposal §7 Stage 5, §9 | RQ-10; recorded as UNKNOWN | OPEN |
| N-01 | NOTE | The proposal permits a Norwegian summary; the repository is English throughout. These documents are English. | proposal header | none | OPEN |
| N-02 | NOTE | The attachment file name carries "v0.3-DRAFT"; the document carries no version. The SHA-256 above identifies the reviewed text. | attachment name | none | OPEN |
| N-03 | NOTE | AC-12 asks later stages to address PR #24's review concerns if code is reused. This branch reuses none; ADR-0003 restates the full rerun comparison independently. | proposal AC-12 | none | OPEN |

## What the proposal gets right

- A–G, v0.1, v0.2, schemas and vectors stay frozen; profiles are optional and additive.
- Non-verdicts are never coerced; expected results stay outside the evaluator.
- Every requirement already has named negative vectors, which made the traceability matrix
  possible without inventing failure conditions.
- The J safety conditions (no live secrets, no traffic outside the test boundary, opt-in
  invasive tests) are concrete.
- REMORA is named as one implementation under test, consistent with CHARTER principle 1.

## Attempts that did not find a problem

- Whether any requirement lacks a failure condition: each of H1–H7, I1–I6 and J1–J6 maps to at
  least one named negative vector (TRACEABILITY.md).
- Whether the proposal changes a frozen file: its decision 1 forbids it, and this PR touches
  only `docs/` and `CHANGELOG.md`.
