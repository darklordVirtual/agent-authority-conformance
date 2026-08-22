# Agent Authority Conformance v0.1

**Status:** draft specification, vendor-neutral. Not a standard, certification, product ranking or general security score.

## 1. Purpose

When an agent runtime says “the tool call was authorized”, that statement can collapse several independent properties into one claim. This specification names seven separable properties so systems built on different assumptions can state precisely what they have demonstrated, what they have not demonstrated, and what they deliberately do not claim.

An assessment produces one status per property, with evidence and scope. The statuses MUST NOT be aggregated.

## 2. The seven properties

### A. Receipt Integrity

**Question:** Can the authorization artifact be verified as authentic, unmodified and currently valid?

In scope: signatures or MACs, tamper detection, expiry, not-before, maximum age, replay semantics, single-use semantics, and binding to an identity or proposal.

Does not imply: legitimate authority provenance (B), exact-call binding (C), or that an external effect occurred (G).

### B. Authority Provenance

**Question:** Can the system establish who or what held authority to authorize the action?

In scope: actor identity, policy authority, reviewer or approver role enforcement, delegation chains and attenuation, tenant scope, and provenance of approved intent.

Does not imply: receipt integrity (A). An authentic artifact can still have been issued by a principal that lacked authority.

### C. Exact-Call Integrity

**Question:** Is the authorization bound to the exact call that is executed?

In scope: tool identity, full argument binding, target, tenant, proposal identity, call identity, immutable binding such as a canonical hash recomputed at dispatch, and resistance to argument substitution under a replayed or reused call identity.

Does not imply: that the exactly bound call was semantically correct (D), or that approved state remained unchanged before execution (F).

### D. Semantic Authority

**Question:** Was the action permitted in its real operational meaning?

In scope: subject, resource, tenant, time window, target system, business intent, expected effect, and the provenance of the meaning used to authorize the action.

An intent constructed solely by the agent from its own proposal is not deployment-owned authority.

Does not imply, and is not implied by, C. A cryptographically exact binding to the wrong account can pass C and fail D.

### E. Execution-Boundary Integrity

**Question:** Can the protected side effect be reached only through the controlled path?

In scope: credential custody, enforcement-point exclusivity, alternative API keys or service accounts, direct SDK or network access, and any other bypass path to the same effect.

A pre-tool hook, interceptor or wrapper is not sufficient evidence by itself. Evidence for E is primarily evidence about credential and execution topology.

### F. TOCTOU Resistance

**Question:** Can approved conditions change between authorization and execution?

In scope: stale approvals, expiry, state or target changes after approval, re-evaluation immediately before dispatch, concurrency across threads, processes and hosts, and distributed races over shared single-use state.

Pre-dispatch validation demonstrates only the interval and concurrency scope directly exercised by the evidence. Single-process evidence does not establish multiprocess behavior.

### G. Effect Verification

**Question:** Does the system verify the actual external effect after execution?

In scope: authoritative read-back, expected-versus-observed postconditions, and explicit distinction between verified, mismatched, unobservable, verifier failure and unsupported verification.

An HTTP 2xx, successful tool return, agent report, receipt or audit record does not by itself prove that the intended external effect occurred.

## 3. Assessment statuses

| Status | Meaning |
|---|---|
| **PASS** | Concrete, relevant and sufficient evidence directly exercises the property at evidence tier `RESOLVED`. |
| **UNTESTED** | The available evidence does not demonstrate the property. |
| **OUT OF SCOPE** | The implementer explicitly does not claim the property. |
| **FAIL** | Concrete, reproducible evidence demonstrates that the property does not hold under a tested condition. |

Normative rules:

1. Absence of evidence MUST be recorded as `UNTESTED`, never `FAIL`.
2. An explicit non-claim MUST be recorded as `OUT OF SCOPE`, never `FAIL`.
3. A partial pass MUST state its supported scope and preserve the untested remainder explicitly.

## 4. Evidence tiers

| Tier | Meaning |
|---|---|
| **RESOLVED** | The assessor inspected the named test, fixture, artifact or code at a stated revision. |
| **REPORTED** | The implementer described evidence that the assessor did not resolve to an artifact. |
| **NONE** | No evidence was offered. |

`PASS` requires `RESOLVED` evidence.

A claim supported only by `REPORTED` evidence remains `UNTESTED` in the assessor's result, while the implementer's claimed status MAY be recorded separately.

## 5. Minimum evidence for PASS

Every `PASS` MUST include:

1. an independently resolvable reference such as a test path and name, fixture, committed result artifact, or code path at an immutable revision;
2. direct exercise of the property;
3. a declared scope, including process model, trust assumptions, and whether effects are real or simulated;
4. a caveat stating what the evidence does not establish.

Evidence that would continue to pass unchanged if the property were removed is not direct evidence for that property.

## 6. Scope declaration

Each assessment MUST declare:

- system name and version;
- immutable revision when available;
- process and deployment model covered by evidence;
- whether external effects are real or simulated;
- relevant trust assumptions;
- explicit non-claims supplied by the implementer.

An assessment without a scope declaration is incomplete.

## 7. Prohibited aggregation

The seven property results MUST NOT be combined into:

- a numeric score or percentage;
- a star rating;
- a grade;
- a “conformance level”;
- a phrase such as “5/7 conformant”;
- a general claim that the system is “secure”.

Comparisons MUST NOT turn the property table into a ranking.

The properties are not commensurable. A deployment may depend critically on E while another depends on G. `OUT OF SCOPE` is a scope decision, not negative credit.

## 8. Applying the model

1. Obtain the implementer's scope declaration and explicit non-claims.
2. Request the most authoritative artifact available for each claimed property.
3. Resolve artifacts to immutable revisions where possible.
4. Assign one status and evidence tier per property with reasoning and caveat.
5. Send the draft assessment to the implementer.
6. Record disagreements rather than silently normalizing them away.

The methodology succeeds when an implementer can recognize their own actual claim boundaries in the result.

## 9. Conformance errors

An assessment is malformed if it:

- grants transitive credit from one property to another;
- treats absent evidence as failure;
- penalizes explicit non-claims;
- reports a `PASS` without resolved evidence;
- omits scope or caveats from a `PASS`;
- aggregates A–G into a score or ranking;
- presents architecture prose or marketing language as direct evidence.

## 10. Known limitations of v0.1

- The seven properties are asserted to be separable, not proven exhaustive.
- Availability, cost control, rate limiting, privacy, data minimization and rollback are outside the present model.
- E currently depends heavily on deployment evidence about credential topology and can be harder to falsify than the other properties.
- Public evidence requirements favor systems with inspectable test suites. This bias is intentional but MUST be disclosed.
- No inter-assessor agreement study has yet established how consistently independent assessors draw the same property boundaries.
- Applying the model to unrelated architectures remains part of the validation work for v0.1.

## 11. Change discipline

Changes that broaden a property MUST include at least one discriminating example demonstrating why the previous boundary was insufficient. New properties SHOULD be proposed only when the claimed behavior cannot be represented without collapsing two distinct authority or execution questions into one.
