# ADR-0003: Strict schemas, a closed combination table and a semantic validator

**Status:** PROPOSED (awaiting maintainer decision)
**Addresses:** adversarial review B-03, S-03; proposal §2.2, §6; AC-02, AC-03, AC-09, AC-10

## Context

The proposal's record carries three result layers: execution, conclusion and assessment.
Without a closed table of allowed combinations, a schema-valid record can say
`execution: COMPLETED`, `conclusion: NOT_ESTABLISHED`, `assessment: PASS`. The proposal's
own illustrative record shows `conclusion: NOT_ESTABLISHED` with `evidence: []`, which is
admissible only if the record also says what evidence is missing. The v0.2 specification
solved the same problem for A–G with a table (§2); the profile records need the same.

## Decision (proposed)

1. **Schema discipline.** JSON Schema Draft 2020-12. `additionalProperties: false` on every
   authoritative object. Aggregate keys (`score`, `overall`, `total`, `aggregate`, `grade`
   and any key the lab already forbids) are refused at every depth with `propertyNames`.
2. **Closed combination table.** Only these rows are valid:

| Execution | Conclusion | v0.2 transcription | Required with it |
|---|---|---|---|
| `COMPLETED` | `ESTABLISHED` | `PASS` only after admission | admitted, revision-pinned evidence; scope; caveat; claim ceiling |
| `COMPLETED` | `CONTRADICTED` | `FAIL` only after admission | the evidence of violation; an admission record before any `FAIL` |
| `COMPLETED` | `NOT_ESTABLISHED` | `NOT_ESTABLISHED` | at least one unresolved obligation |
| `NOT_RUN` | `NOT_APPLICABLE` | `OUT_OF_SCOPE` | the evidenced reason the profile does not apply (for example a proved-unreachable class) |
| `NOT_RUN` | `NOT_RUN` | `UNTESTED` | none beyond the record header |
| `UNSUPPORTED` | `INCOMPATIBLE` | none | `verifier_error`; the implementation cannot present the input contract |
| `INVALID_INPUT`, `ERROR`, `NOT_ADMITTED` | none (`null`) | none | `verifier_error` |

   A conclusion before admission carries no v0.2 transcription. A non-verdict is never
   converted to a conclusion (AC-03). `NOT_APPLICABLE` needs evidence, because omission
   must not turn into a pass (proposal §5).
3. **Semantic validator** (Stage 1), beyond schema shape:
   - commit and digest syntax; every evidence pin resolves to a listed fixture or subject file;
   - scope consistency: the claim, every evidence item and the subject name the same scope;
   - one record per (profile, revision, claim, subject revision) within a record set;
   - unknown profile identifiers or revisions are refused (fail closed);
   - the declared BCR level is consistent with the declared roles: if the producer is the
     operator, the level is BCR-0; if the producer authored the verifier, it is at most
     BCR-1; BCR-3 or higher requires a verifier author other than the producer. The
     validator refuses an inconsistent level; it cannot prove a consistent one;
   - AI drafting is disclosed whenever any field was drafted by an agent.
4. **Rerun comparison** covers the whole record: execution, conclusion, witness, error,
   class, message, scope and evidence links (AC-10). This matches the comparison the lab
   adopted in PR #24 after review; it is restated here because this SDD must not depend on
   PR #24.

## Consequences

- The Stage 1 acceptance fixtures (SCHEMA-ACCEPTANCE-CRITERIA.md) include one invalid
  record for every forbidden combination.
- Roles become required fields, since the level check depends on them.

## Open point

Whether `NOT_ADMITTED` belongs in profile records or only in lab runs. It is listed here so
the table stays closed whichever way it is decided (RESEARCH-QUESTIONS.md RQ-09).
