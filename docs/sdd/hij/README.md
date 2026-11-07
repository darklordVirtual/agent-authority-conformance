# SDD-AACP-HIJ-001: Stage 0 review package

**Status:** proposal under review. Documentation only. Nothing here is an adopted AACP
profile, schema, vector or result, and nothing here asserts a property of REMORA or of any
other implementation.

| Item | Value |
|---|---|
| Proposal | [`docs/sdd/SDD-AACP-HIJ-001.md`](../SDD-AACP-HIJ-001.md), committed verbatim |
| Proposal SHA-256 | `9b7c8d8f5ec60654df9117fc6e7a3b33cc123a844c49f4c8e7955a5e383b1cc4` |
| Baseline | `main@30a5982ba48ac899953abc14d2be7d9bbd9fa200` |
| Depends on PR #24 | No. This branch starts from the baseline; PR #24 is unmerged. |
| Stage | 0 of 5: design freeze and review |
| Gate to Stage 1 | Every item marked BLOCKING in the adversarial review has a recorded maintainer disposition, and ADR-0001 to ADR-0004 are accepted or amended |

The proposal is kept byte-for-byte as submitted. Amendments are made in the ADRs and the
review below, never by editing the proposal, so the record shows what was proposed and what
was decided.

## Contents

| Document | Purpose |
|---|---|
| [adr/ADR-0001-property-separation.md](adr/ADR-0001-property-separation.md) | H, I and J are profiles with a declared A–G relationship, not new properties; identifiers and non-transitivity |
| [adr/ADR-0002-versioning-and-record-format.md](adr/ADR-0002-versioning-and-record-format.md) | Frozen integer revisions; profile results as `bcr-run-v1` records versus a separate envelope |
| [adr/ADR-0003-strict-schema-and-semantic-validation.md](adr/ADR-0003-strict-schema-and-semantic-validation.md) | Strict schemas, the allowed result-combination table and the semantic validator |
| [adr/ADR-0004-j-single-profile-or-family.md](adr/ADR-0004-j-single-profile-or-family.md) | Whether J is one narrow profile or a family of independent profiles |
| [DRAFT-CLAIMS.md](DRAFT-CLAIMS.md) | Draft normative claims, failure conditions, counterexamples, claim ceilings and non-claims for review |
| [SCHEMA-ACCEPTANCE-CRITERIA.md](SCHEMA-ACCEPTANCE-CRITERIA.md) | What the Stage 1 schemas and validator must accept and refuse |
| [TRACEABILITY.md](TRACEABILITY.md) | Every requirement mapped to the test that will check it, all PLANNED |
| [CHECKLIST.md](CHECKLIST.md) | Implementation checklist with gates per stage |
| [RESEARCH-QUESTIONS.md](RESEARCH-QUESTIONS.md) | Unresolved research questions, kept non-normative |
| [reviews/STAGE-0-ADVERSARIAL-REVIEW.md](reviews/STAGE-0-ADVERSARIAL-REVIEW.md) | Adversarial review of the proposal against CHARTER, METHOD, TERMINOLOGY, GOVERNANCE and v0.2 |

## Ground rules carried into every later stage

- A–G definitions, the v0.1 and v0.2 specifications and schemas, committed assessments,
  frozen vectors and CI gates stay unchanged (proposal decision 1; AC-01).
- REMORA is one implementation under test with no reference semantics (CHARTER principle 1).
  No evaluator, vector or expected result may be derived from a REMORA run.
- No aggregate score, grade, percentage or project-level verdict in any artifact (CHARTER
  principle 6; AC-09).
- Specification before tests, tests before code: a requirement has a planned test in
  TRACEABILITY.md before any code for it is written, and a test is never edited to match
  an implementation's output.
- An adversarial review closes every stage before the next begins. Pull requests are not
  merged automatically.

Drafted with AI assistance (agent: claude-opus-5.5) for maintainer review.
