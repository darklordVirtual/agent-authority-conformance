# Bounded Claim Reproduction (BCR)

BCR is the evidence method AACP results are recorded in. A BCR result answers
one question:

> Could this implementation reproduce this exact claim, under these exact
> conditions?

It does not answer whether the system is secure.

## The chain

```text
CLAIM -> PROFILE -> IMPLEMENTATION UNDER TEST -> RUN -> NEGATIVE CONTROLS -> EVIDENCE -> CLAIM CEILING
```

A profile fixes the claim, the input contract, the positive and negative
fixtures, the evaluation procedure and the claim ceiling. A run binds a
revision of the implementation to a revision of the profile. Negative
controls (mutation, replay, malformed, stale and wrong-subject cases) show the
evaluation can fail. The record states the ceiling again, so a reader of the
record alone cannot read more into it than the profile claims.

## Levels

A BCR record states one level. The level describes who ran what, and nothing
about the strength of the implementation.

| Level | Name | Conditions |
|---|---|---|
| BCR-0 | SELF | the producer's code, fixtures, runner and execution; a development test, no external evidence |
| BCR-1 | REPRODUCTION | another party runs the producer's fixtures and runner; establishes reproducibility, not implementation independence |
| BCR-2 | SECOND IMPLEMENTATION | another party implements the evaluation logic without importing the producer's verifier, but one independence condition is still unmet |
| BCR-3 | INDEPENDENT RECOMPUTATION | the external party implements the verifier, recomputes the expected property, runs the negative and mutation cases from the pinned public specification, and needs no producer maintainer during the run |
| BCR-4 | INDEPENDENT HOST | BCR-3, with the external party controlling environment, runner, execution and evidence capture, and publishing retained evidence |

BCR-4 is strong external evidence. It is still not certification.

REMORA's `interop-result-v1` levels `L0_SELF_TEST` to `L4_INDEPENDENT_HOST_RUN`
map one to one onto BCR-0 to BCR-4.

## Result vocabulary

A result is never a bare pass or fail. The planned `bcr-run-v1` schema records
one of:

| Result | Means |
|---|---|
| `ESTABLISHED` | the run reproduced the claim under the profile |
| `CONTRADICTED` | the run produced evidence against the claim |
| `NOT_ESTABLISHED` | the procedure ran and the evidence supports neither |
| `NOT_APPLICABLE` | the profile does not apply to this implementation's declared scope |
| `INCOMPATIBLE` | the implementation cannot present the profile's input contract |
| `NOT_RUN` | no applicable procedure was completed |

The v0.1 and v0.2 assessment schemas keep their own status vocabulary; they
are preserved, not rewritten. A `bcr-run-v1` record is a new document type
that will sit beside them, with `schema/federation-run-v1.schema.json` as its
starting point.

## A record, in outline

```json
{
  "profile": "AACP-EXACT-CALL-BINDING-1",
  "method": "BCR",
  "level": "BCR-3",
  "implementation": {"name": "...", "revision": "..."},
  "evaluator": {"project": "...", "revision": "..."},
  "claim": "authorized call equals dispatched call",
  "result": "ESTABLISHED",
  "positive_cases": "n/n",
  "negative_cases": "n/n",
  "mutants_detected": "n/n",
  "claim_ceiling": ["does not establish ..."]
}
```

Counts are reported as fractions per class, never as one aggregate.
