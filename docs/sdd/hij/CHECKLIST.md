# Implementation checklist: SDD-AACP-HIJ-001

Tick an item only when its evidence is linked. A stage starts only after the previous stage's
gate is ticked by the maintainer. No pull request is merged automatically.

## Stage 0: design freeze (documentation only, this PR)

- [x] Proposal committed verbatim with its SHA-256 (`docs/sdd/SDD-AACP-HIJ-001.md`)
- [x] Branch from `main@30a5982`; no dependency on unmerged PR #24
- [x] ADR-0001 property separation and identifiers
- [x] ADR-0002 revisions and record format
- [x] ADR-0003 strict schema, combination table, semantic validator
- [x] ADR-0004 agent cyber profile family
- [x] Draft normative claims, failure conditions, counterexamples, ceilings (DRAFT-CLAIMS.md)
- [x] Stage 1 schema acceptance criteria (SCHEMA-ACCEPTANCE-CRITERIA.md)
- [x] Traceability matrix, all rows PLANNED (TRACEABILITY.md)
- [x] Research questions (RESEARCH-QUESTIONS.md)
- [x] Adversarial review of the proposal (reviews/STAGE-0-ADVERSARIAL-REVIEW.md)
- [x] No code, schema, vector, test or CI change in this PR (checked in the PR description)
- [x] Stage 0 separate-reviewer prerequisite **explicitly waived by maintainer** (2026-11-07); not represented as independently reviewed; see ADR-0004 and Stage 0 adversarial review
- [x] Maintainer accepted ADR-0004 option 2: five cyber boundary profiles and one observation-prerequisite profile (2026-11-07); B-05 disposition recorded
- [ ] Maintainer disposition for **remaining** BLOCKING findings B-01–B-04 and B-06 (B-05 addressed)
- [ ] Maintainer decisions on ADR-0001 to ADR-0003 (ADR-0004 accepted)
- [ ] **Gate 0:** profile semantics and schema acceptance criteria reviewed; maintainer records remaining decisions and explicitly closes gate

## Stage 1: contracts (schema and registry PR)

- [ ] Failing tests for SA-1 to SA-5 written first and seen to fail
- [ ] Record schema per ADR-0002 (`bcr-run-v1`, or the envelope with its tested mapping)
- [ ] Profile-definition schema (six parts plus claim ceiling)
- [ ] Registry: identifiers and integer revisions, fail closed on unknown ones
- [ ] Semantic validator (ADR-0003)
- [ ] Legacy byte pins and output snapshot (SA-1)
- [ ] Adversarial review: attempt to construct a scoring, ranking or evidence-free passing record
- [ ] **Gate 1:** malformed verdicts and unsupported revisions fail; legacy output identical; no scoring possible

## Stage 2: cumulative authority limits

- [ ] Input contract and every vector frozen and digest-pinned before the evaluator
- [ ] H-NEG-01 to -12, H-POS-01 to -05, H-DISC-01 failing first, then passing
- [ ] Seeded mutants: non-atomic ledger, missing fail-closed path, wrong approver count, premature release
- [ ] Mutation survivors disclosed, none hidden by test edits
- [ ] Counterexample pairs against D and F (AC-08)
- [ ] Optional adapters (REMORA or others) only after the evaluator is frozen, never as oracle
- [ ] Adversarial review
- [ ] **Gate 2**

## Stage 3: cryptographic authority integrity

- [ ] Raw-byte vectors, preimage contracts, trust-material records frozen
- [ ] Decision on RQ-05 (crypto library in the reference evaluator)
- [ ] RFC 8032 §7.1 vectors plus cross-implementation vectors
- [ ] I-NEG-01 to -12 and I-NV-01
- [ ] Counterexample pairs against A (one-way), B and C
- [ ] Adversarial review
- [ ] **Gate 3**

## Stage 4: agent cyber family (one sub-stage per class if ADR-0004 option 2)

- [ ] Threat model per class: zone, attacker capability, assets, interval, sources
- [ ] Isolated fake tool, network and secret services; fake canary format
- [ ] Observation prerequisite with seeded positive controls
- [ ] Negative vectors per class and legitimate workflows
- [ ] Live or invasive tests opt-in only, behind a separate execution mandate
- [ ] Adversarial review per class
- [ ] **Gate 4**

## Stage 5: integration and reproducibility

- [ ] Full CI, mutation checks, schema agreement, package and rerun integrity
- [ ] Second evaluator reproduces frozen outputs without implementation-specific imports
- [ ] At least one non-REMORA implementation per applicable profile (RQ-10)
- [ ] Cross-project comparison without ranking; all negative findings kept
- [ ] **Gate 5:** every acceptance criterion, provenance item and review concern closed
