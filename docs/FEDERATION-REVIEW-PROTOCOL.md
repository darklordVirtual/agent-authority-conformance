# Federation review protocol v1

**Status:** experimental review protocol. It is not a certification programme,
standard, ranking system or claim of federation endorsement.

This protocol operationalizes a narrow pattern discussed in
`aeoess/agent-governance-vocabulary#177`: independent projects keep their own
architecture while shared boundaries use pinned artifacts, per-claim results,
provenance and explicit claim ceilings.

## 1. Respect and consent

A cross-project review starts from a maintainer-proposed artifact, a public
invitation to verify it, or explicit permission. Public availability alone is
not treated as permission to publish an evaluative report about a project.

Before an evaluative run, record:
1. subject repository and full commit SHA;
2. exact public artifacts and hashes;
3. adapter and procedure revision;
4. named claims and non-claims;
5. synthetic, simulated, reproduced or independently observed evidence class;
6. review recipients and publication rule;
7. whether mutations or derived artifacts are permitted.

No private artifact is made public by AAC. A private first review remains private
until the agreed release condition is satisfied.

## 2. Four separate stages

**Resolution** answers whether the exact declared bytes were obtained.
**Admission** answers whether those bytes are relevant, provenance-bound,
applicable and trusted enough for a named procedure.
**Inference** answers only the named AAC property question.
**Review/publication** gives the producer a chance to identify factual errors,
scope mistakes or stronger primary evidence before release.

These stages MUST NOT inherit credit automatically.

`RESOLVED` is not `ADMITTED`. `ADMITTED` is not `PASS`. A valid signature
is not execution evidence. A successful dispatch is not effect verification.
Silence from a maintainer is not approval.

## 3. Run freeze

The run manifest is frozen before execution. A material change to subject bytes,
adapter logic, procedure, expected semantics or scope creates a new run identity.

Expected fixture answers stay outside inference input. If the procedure cannot
run, report `UNSUPPORTED`, `INVALID_INPUT` or `ERROR` rather than a property
failure. If it runs but evidence cannot decide the claim, use
`NOT_ESTABLISHED` and name the unresolved obligation.

## 4. Source classes and independence

At minimum distinguish producer artifact, source code, test fixture, run record,
review record and independent observation. Re-running producer-authored fixtures
is a reproduction or second implementation when appropriate, not automatically
independent validation.

Evidence created by the project under review may be excellent evidence of
internal consistency while still being insufficient for an external-effect or
observation-completeness claim.

## 5. Output package

A publishable run should contain:
- immutable subject and adapter pins;
- machine-readable evidence bundle;
- exact procedure and reproduction command;
- one result per named claim;
- unresolved obligations;
- explicit non-claims and claim ceiling;
- source class for every material evidence item;
- disagreements/corrections from maintainer review;
- run lineage when a rerun supersedes or extends an earlier result.

Never replace per-claim output with an aggregate score.

## 6. Maintainer review

The default state is `DRAFT_PRIVATE_REVIEW`. Review asks the producer to check
facts, artifact interpretation, scope and terminology. It does not ask the
producer to approve AAC's conclusion.

Corrections to facts are incorporated with lineage. Technical disagreement is
recorded rather than silently rewritten. New producer evidence creates a new
evidence revision if it changes the basis of inference.

Publication must state whether the producer reviewed the report and whether any
remaining disagreement exists. "Reviewed" does not mean "endorsed".

## 7. Mutation and adequacy

Mutation testing is a separate experiment. It tests whether the pinned corpus can
distinguish agreed seeded faults. A surviving mutant is a corpus discrimination
limit unless stronger analysis establishes another classification. It is not by
itself proof that the producer checker is wrong.

Positive and inert controls, exact mutant diffs and all survivors are retained.
Do not curate away inconvenient survivors after seeing the result.

## 8. REMORA as a metatest subject

REMORA may be used to test AAC's adapter and evidence semantics because it has
explicit claim/capability registers, deterministic conformance artifacts and
documented negative results. This does not grant REMORA privileged status.

In particular, REMORA's evidence-sufficiency work requires synthetic accepted
premises to stay visibly synthetic and forbids production adapters from treating
caller-controlled completeness booleans as proof. AAC adopts that lesson as a
general adapter invariant: accepted-premise fields require provenance and an
admission step outside the producer-controlled payload.

REMORA results used here retain their own maturity labels. Internal benchmarks,
regression tests and author-run synthetic corpora are not relabelled as field
validation or independent replication.

## 9. Stop conditions

Stop and return to review when the subject pin changes, an artifact cannot be
resolved, a claim depends on an undeclared trust assumption, expected results
leak into verifier input, an adapter needs broader access than agreed, or the
output would support a stronger public interpretation than the evidence ceiling.

The objective is useful disagreement and reproducible learning, not making more
projects pass.
