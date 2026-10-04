# Agent Authority Conformance v0.2

> Published under the project's former name. The project is now Agent Authority Conformance Profiles (AACP); this specification is preserved as written and its requirement set is frozen. See [TERMINOLOGY.md](TERMINOLOGY.md#names).

**Status: draft.** Vendor-neutral; not a standard, certification, ranking or
general security score. v0.1 remains available without reinterpretation.

## 1. Relationship to v0.1

The A–G definitions, separation of properties, evidence tiers, scope discipline,
prohibition on aggregation, and limitations in [v0.1](SPECIFICATION.md) still
apply. This document overrides v0.1 §§3, 9 and 12 where specified below. It adds
an evidence-sufficiency distinction and machine-checkable reporting constraints;
it does not add an eighth property.

The normative v0.2 format is [assessment-v0.2.schema.json](schema/assessment-v0.2.schema.json),
plus the cross-field scope equality rule in §5. A schema-valid assessment is
well-formed; it is not proof that its evidence is authentic, sufficient or true.

## 2. Separate verification execution from the property verdict

Every property row MUST carry `verification_status` and `status`:

| verification_status | Allowed status | Meaning |
|---|---|---|
| `NOT_RUN` | `UNTESTED` | No applicable procedure has been completed. |
| `NOT_RUN` | `OUT_OF_SCOPE` | Explicit non-claim for the declared assessment scope. |
| `COMPLETED` | `PASS` | Admissible, resolved evidence establishes the bounded property. |
| `COMPLETED` | `FAIL` | Admissible, resolved evidence demonstrates a violation in scope. |
| `COMPLETED` | `NOT_ESTABLISHED` | The applicable procedure ran; evidence supports neither establishment nor violation. |
| `UNSUPPORTED` | `null` | No supported verification procedure was available. |
| `INVALID_INPUT` | `null` | Malformed input prevented applicable verification. |
| `ERROR` | `null` | The verifier failed to complete its procedure. |

`UNSUPPORTED`, `INVALID_INPUT` and `ERROR` MUST have a `verifier_error` containing
`code` and `message`. They MUST NOT be converted to `NOT_ESTABLISHED` or `FAIL`.
A verifier crash is not evidence that the evaluated property failed.

Completed verification MUST identify its `procedure` at a pinned revision and
its `evaluation_scope`. `NOT_ESTABLISHED` MUST name at least one unresolved proof
obligation in `unresolved_obligations`. Completed `PASS` and `FAIL` MUST carry an
empty obligation list. The procedure may be an explicitly recorded manual
assessment; running an unrelated test does not qualify.

`runtime_outcome` and `receipt_chain_outcome` are optional descriptive fields on
separate axes. A successful tool return, disclosed receipt gap or matched test
expectation grants no automatic property credit. Expected fixture answers MUST
remain outside checker input.

## 3. Evidence and assessment integrity

For `PASS` and `FAIL`, `evidence_tier` MUST be `RESOLVED`, and `evidence` MUST
contain at least one reference at a pinned revision. `PASS` also requires a
nonempty `supported_scope`. Both retain the required reasoning and caveat.
Partial passes MUST preserve their `untested_remainder` explicitly.

`RESOLVED` means an assessor inspected an artifact, as in v0.1. It does not alone
establish sufficiency. A path string, boolean, hash or self-declaration does not
become authoritative merely because it is well-formed. Evidence admission must
establish relevance, provenance, applicability and trust under the declared
evaluation context before inference.

Each property ID may appear at most once and MUST match its canonical A–G name.
The record may assess a subset; omitted rows grant no credit. Dates MUST be real
calendar dates. Aggregate score fields remain unsupported and aggregation in
prose remains prohibited.

Missing evidence is never by itself `FAIL`. Before verification it is `UNTESTED`;
after an applicable procedure ran without sufficient evidence it may be
`NOT_ESTABLISHED`. Do not mechanically relabel historical `UNTESTED` records.

An explicit non-claim is a scope declaration, not a mechanism for erasing a
demonstrated violation in that same scope. Preserve the violating record. A
separate refused configuration can be `OUT_OF_SCOPE` only under the refusal
conditions in v0.1 §12.3, with the original bypass retained.

## 4. E: bounded non-bypassability and observation coverage

v0.1 §12's drift-checked credential register, reasoned agent zone and named
bypass attempts remain required for an E `PASS`. The five minimum attempt
classes have these machine-readable names:

| Name | Attempt |
|---|---|
| `without_authorization` | Dispatch without authorization. |
| `unregistered_tool` | Dispatch an unwrapped or unregistered tool name. |
| `extracted_callable` | Extract and invoke the guarded callable. |
| `shared_process_credential` | Read/use credentials from a shared process. |
| `authenticated_client` | Reach the effect through an authenticated client, pool or subprocess. |

Additional relevant classes SHOULD be attempted. A blocked attempt MUST NOT be
attributed to a particular enforcement boundary without accepted attribution
evidence and an isolating control. An observed alternative path reaching the
protected effect establishes `FAIL` within its scope, even if topology or
observation coverage is incomplete. This supersedes the unconditional
"without both halves, UNTESTED" rule in v0.1 §12 for new v0.2 assessments.

If no bypass is observed, the verifier MUST NOT infer absence solely from a
successful governed path or a refusal-only log. A bounded E `PASS` requires both
the topology and bypass evidence, plus accepted evidence that observation is
complete for the declared evaluation scope. Producer capability or field
visibility alone does not establish coverage over every relevant event in an
interval. An upstream coverage assessment must address these distinct premises
where applicable; this verifier does not establish them recursively.

The scope MUST identify the agent zone, deployment/configuration, protected
effect, observation interval and relevant attempt classes unambiguously. An
evaluation-scope identifier is bound to that definition; changing the zone or
interval requires a new identifier and matching evidence. Evidence for one
invocation cannot satisfy a session-wide claim.

No observed bypass with incomplete or mismatched coverage yields
`NOT_ESTABLISHED` after applicable verification, with `observation_coverage` as
an unresolved obligation. Missing topology, missing attempted classes and
unknown attempt outcomes likewise remain explicit obligations. Unsupported
verification and malformed observations stay on the separate execution axis.

An E `PASS` MUST be expressed as **no demonstrable alternative path within the
declared zone, observation scope and attempted classes**. It is not universal
non-bypassability. The assessor-chosen zone, incomplete static-analysis risk,
and source-access asymmetry of v0.1 §12.4 MUST remain in the caveat.

## 5. Machine-readable E evidence

An E `PASS` additionally requires `execution_boundary` with:

- `evaluation_scope`, exactly equal to the property row's `evaluation_scope`;
- `agent_zone`, with the declared roots/closure and their justification resolved
  through the referenced topology artifact;
- `attempted_bypass_classes`, including the five minimum classes;
- pinned `topology_evidence`, `coverage_evidence` and nonempty `bypass_evidence`.

The JSON Schema enforces presence and shape. `validate_assessment()` also
enforces scope equality. Neither validates the truth of an evidence reference
or performs credential scanning. An assessor still has to establish the content
requirements above and include relevant evidence in the row's `evidence` list.

## 6. Bounded reference rule and corpus

[`conformance/boundary.py`](conformance/boundary.py) implements only the E
decision rule over **already accepted evidence**. Its input schema requires
explicit topology/coverage descriptors (or `null`) and scoped attempt outcomes.
It rejects missing descriptors instead of inventing defaults. All input is
validated before inference; unsupported property IDs yield a non-verdict.

`accepted_topology` means the upstream assessor has already checked v0.1 §12.1's
register, drift conditions, roots/closure and caveats for this scope.
`accepted_coverage` means that assessor has independently established the
required observation coverage, including capability/visibility and interval
completeness where relevant. Attempt records are accepted observations of a
blocked, successful or unknown bypass with pinned source references. `BLOCKED`
does not itself identify which component caused the refusal.

The checker compares scopes and applies the inference rule. It does not resolve
URLs, validate signatures, establish these premises, inspect source code, invoke
tools or contact a deployment. Untrusted agent-supplied claims MUST NOT be fed
directly into this accepted-evidence interface. The interface is a reference
for an inference boundary, not a deployable security enforcement point.

The committed fixtures are synthetic, with stipulated premises marked as such.
They demonstrate decision semantics; they do not assess REMORA, AEGIS or a live
deployment. A conditional fixture `PASS` is not a product conformance claim.

`python -m conformance.check` reads committed inputs and expected results
without modifying them. Expected results never enter `evaluate()`. A mismatched
expectation exits nonzero. Automated tests mutate evidence, scopes, descriptors
and expectations to expose false passes and silent fixture repair.

## 7. Provenance and status

This draft draws on the discussion in
[CoSAI/OASIS WS4 RFC #189](https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/issues/189),
including [separation of verifier input and harness expectations](https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/issues/189)
and [scope-bound coverage and read-only verification](https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/issues/189#issuecomment-5672817487).
The repository remains an independent specification. These references do not
claim CoSAI adoption, endorsement or certification. The RFC is work in progress.

The new fixture set was authored here. It does not copy or re-identify REMORA
vectors V-02 or V-13 as non-bypassability cases, and it does not modify external
corpora or their expected results.
