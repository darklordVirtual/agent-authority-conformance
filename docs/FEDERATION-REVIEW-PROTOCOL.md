# Federation review protocol v1

**Status:** experimental review protocol. It is not a certification programme,
standard, ranking system, membership registry or claim of Federation endorsement.

The protocol operationalizes a narrow pattern from
`aeoess/agent-governance-vocabulary#177`: independent projects keep their own
architecture while shared boundaries use pinned artifacts, per-claim results,
provenance and explicit claim ceilings.

## 1. Project sovereignty and consent

A cross-project review starts from a maintainer-proposed artifact, a public
verification request or explicit permission. Public artifacts may be resolved
without executing producer code. An evaluative publication follows the review
policy frozen for that pilot.

Producer review is for factual corrections, scope mistakes and stronger primary
evidence. It is not automatically a veto over a verifier conclusion. Any
remaining technical disagreement is preserved in the public record when the
frozen policy permits publication.

## 2. Five separate stages

1. **Resolution**: did the assessor obtain the exact declared bytes?
2. **Admission**: are those bytes relevant, provenance-bound and applicable?
3. **Inference**: what does the named procedure establish?
4. **Review**: did the producer identify factual/scope corrections or disagreement?
5. **Publication**: does the frozen policy permit release?

No stage inherits credit automatically. `RESOLVED` is not `ADMITTED`.
`ADMITTED` is not `PASS`. A valid signature is not execution evidence.
A successful dispatch is not effect verification.

## 3. Review and publication policy

Every adapter freezes one policy:

- `PRIVATE_UNTIL_APPROVED`
- `PUBLIC_AFTER_REVIEW`
- `PUBLIC_IMMEDIATE`
- `PUBLIC_BY_MUTUAL_CONSENT`

For time-bounded review, record `review_window_days`. Record whether producer
review is `REQUIRED`, `OPTIONAL` or `NOT_REQUIRED`, and what happens to an
unresolved disagreement: publish it, hold publication, or supersede with a new
run. Silence is never rewritten as endorsement.

## 4. Run identity and independence

A material change to subject bytes, adapter logic, procedure, scope or expected
semantics creates a new run identity. A `federation-run-v1` record separates:

- producer;
- fixture author;
- verifier implementation maintainer;
- runner/operator;
- subject, adapter and procedure pins;
- exact command and runtime environment;
- blinded/non-blinded state;
- independence classification.

Supported classifications are `AUTHOR_RUN`, `REPRODUCTION`,
`SECOND_IMPLEMENTATION` and `INDEPENDENT_IMPLEMENTATION`. The classification
describes provenance. It does not itself make a claim correct.

## 5. Native claims are preserved

AAC does not force every foreign claim into A-G. An adapter may preserve a
producer's native claim and separately describe its relationship to an AAC
property as `exact`, `structural`, `partial`, `false_analog`,
`no_mapping` or `not_evaluated`.

A mapping is metadata, not transitive credit. Foreign result vocabularies remain
the producer's vocabulary unless a separately versioned inference procedure
explicitly evaluates an AAC property.

## 6. Source classes

At minimum distinguish producer artifact, source code, test fixture, run record,
review record and independent observation. Re-running producer-authored fixtures
is not automatically independent validation.

## 7. Output and edge records

A publishable run contains immutable pins, a machine-readable evidence bundle,
run manifest, command, per-claim results, unresolved obligations, explicit
non-claims, claim ceiling, evidence source classes, review record and lineage.

A `federation-edge-record-v1` may summarize one producer-to-consumer technical
edge. It is descriptive only: it does not establish membership, endorsement,
commercial status or governance authority.

## 8. Mutation and adequacy

Mutation testing is a separate experiment. It measures whether a pinned corpus
distinguishes agreed seeded faults. Survivors are retained and described as
discrimination limits unless stronger analysis establishes another result.

## 9. Stop conditions

Stop and return to review if a pin changes, an artifact cannot be resolved,
expected answers leak into verifier input, a procedure needs broader access than
agreed, a trust assumption is undeclared, or public wording would exceed the
claim ceiling.

The objective is useful disagreement and reproducible learning, not making more
projects pass.
