# Stage 1 schema and validator acceptance criteria

**Status:** DRAFT for Stage 0 review. Written so each line becomes one failing test before any
schema or validator code exists. Field names are provisional until ADR-0002 settles the record
format; the criteria hold for either format.

## SA-1 Legacy preservation (AC-01)

| ID | Criterion | How it is checked |
|---|---|---|
| SA-1.1 | `SPECIFICATION.md`, `SPECIFICATION-v0.2.md`, `schema/assessment.schema.json` and `schema/assessment-v0.2.schema.json` are byte-identical to `main@30a5982` | SHA-256 pins in a test (v0.1 is already pinned by `tests/test_conformance.py`; extend to the v0.2 files) |
| SA-1.2 | Every committed assessment and fixture validates with the same output as at the baseline | snapshot of `python -m conformance.check` output at the baseline, compared byte for byte |
| SA-1.3 | Frozen reference vectors unchanged | existing `python -m conformance.vectors verify` and `scripts/build_reference_vectors.py --check` |
| SA-1.4 | Existing CI jobs keep their steps; new jobs are additive | review of the workflow diff |

## SA-2 Shape (AC-02, AC-09)

A record set must be **refused** when any of these holds; each is one invalid fixture:

1. an unknown field on any authoritative object;
2. an aggregate key (`score`, `overall`, `total`, `aggregate`, `grade`) at any depth;
3. a profile identifier of `H`, `I` or `J`, or any identifier not in the registry;
4. a profile revision not in the registry, or a non-integer revision such as `1.0.0-draft`;
5. a commit that is not 40 lowercase hex characters, or a digest that is not 64;
6. two records for the same (profile, revision, claim, subject revision);
7. a percentage, fraction headline or grade in any free-text summary field the schema
   defines (for example a `summary` field containing "10/10"), where such fields exist.

## SA-3 Combinations (ADR-0003 table; AC-03)

One valid fixture per allowed row, and one invalid fixture for each of these:

| Invalid combination | Reason |
|---|---|
| `COMPLETED` with no conclusion | a completed procedure must conclude |
| a non-verdict execution with a conclusion | non-verdicts are never coerced |
| a non-verdict without `verifier_error` | the reason must be recorded |
| `ESTABLISHED` without admitted, pinned evidence | no credit without evidence |
| `PASS` transcription without an admission record | admission precedes PASS |
| `FAIL` transcription from `CONTRADICTED` without an admission record | a bounded violation is not a product verdict |
| `NOT_ESTABLISHED` without an unresolved obligation | the gap must be named |
| `NOT_APPLICABLE` without the evidence for non-applicability | omission must not pass |
| `ESTABLISHED` for an agent cyber class without its observation prerequisite | blind detector rule (ADR-0004) |

## SA-4 Semantics (ADR-0003 validator)

| ID | Refused when |
|---|---|
| SA-4.1 | an evidence pin does not resolve to a listed fixture or subject file |
| SA-4.2 | claim, evidence and subject declare different scopes |
| SA-4.3 | the declared level is inconsistent with the roles (producer as operator above BCR-0; producer-authored verifier above BCR-1; BCR-3 or BCR-4 with the producer as verifier author) |
| SA-4.4 | any field is agent-drafted and AI assistance is not disclosed |
| SA-4.5 | expected results appear inside the evaluator's input |

## SA-5 Reproducibility (AC-10)

A rerun comparison reports a divergence when any of these differs: execution, conclusion,
witness, error, class, message, scope, evidence links. A package with a missing, changed or
unlisted file is `NOT_REPRODUCIBLE`, never `REPRODUCED`.

## SA-6 Gate for Stage 1 (proposal §7)

Stage 1 is complete when SA-1 to SA-5 each have passing tests, every invalid fixture is
refused for the stated reason (asserted on the error, not only on failure), legacy outputs are
identical, and an adversarial review has tried to construct a record that scores, ranks or
passes without evidence and failed.
