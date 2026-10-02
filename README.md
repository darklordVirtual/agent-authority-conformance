# Agent Authority Conformance

> **Evidence before adjectives.** A vendor-neutral vocabulary for evaluating authority and execution controls in agentic systems.

> **Project identity:** this repository is an independent project. It is not the `Agent-Authority-Conformance/aps-conformance-suite` project, not a Federation authority, and not a membership or certification body.

**Status:** Draft v0.2 (opt-in; v0.1 preserved) · **No aggregate score** · **Not a certification** · **Not a product ranking**

When an agent runtime says *“the tool call was authorized”*, that statement hides several independent security and governance questions. Agent Authority Conformance separates those questions so implementations can state precisely what they have demonstrated, what remains untested, and what they deliberately do not claim.

The project evaluates **evidence**, not marketing language.

## The seven properties

| ID | Property | Core question |
|---|---|---|
| **A** | Receipt Integrity | Is the authorization artifact authentic, unmodified, valid and correctly replay-bounded? |
| **B** | Authority Provenance | Can the system establish who or what had authority to approve the action? |
| **C** | Exact-Call Integrity | Is authorization bound to the exact tool call that is executed? |
| **D** | Semantic Authority | Was the action permitted in its real operational meaning? |
| **E** | Execution-Boundary Integrity | Can the protected effect be reached only through the governed path? |
| **F** | TOCTOU Resistance | Can approved conditions change between authorization and execution? |
| **G** | Effect Verification | Does the system verify the actual external effect after execution? |

These properties are deliberately **separable**. Evidence for one property grants no credit in another.

## Federation interop surface

The optional Federation layer is read-only and non-authoritative. It provides:
- immutable evidence adapters;
- native-claim preservation and explicit A-G crosswalk relationships;
- a run manifest separating producer, fixture author, verifier implementation and runner;
- explicit independence/blinding classification;
- configurable review/publication policy;
- descriptive edge records with claim ceilings.

Start with [the review protocol](docs/FEDERATION-REVIEW-PROTOCOL.md),
[native claim mapping](docs/NATIVE-CLAIM-MAPPING.md),
[adapter contract](adapters/README.md) and [review checklist](docs/REVIEW-CHECKLIST.md).

## Assessment statuses

v0.2 records verification execution separately from the property result:

| Verification | Property status | Meaning |
|---|---|---|
| `NOT_RUN` | `UNTESTED` | No applicable verification completed. |
| `NOT_RUN` | `OUT_OF_SCOPE` | Explicit non-claim within the assessment scope. |
| `COMPLETED` | `PASS` / `FAIL` | Resolved evidence establishes the bounded property or its violation. |
| `COMPLETED` | `NOT_ESTABLISHED` | Procedure ran but evidence supports neither conclusion. |
| error state | `null` | Structured non-verdict. |

## One rule matters most

**Do not aggregate A-G into a score.** No percentage, star rating, security grade
or ranking is valid under this model.

## Repository map

| Path | Purpose |
|---|---|
| `SPECIFICATION-v0.2.md` | Draft v0.2 semantics |
| `schema/assessment-v0.2.schema.json` | v0.2 assessment schema |
| `schema/federation-adapter-v1.schema.json` | foreign-artifact resolution contract |
| `schema/federation-evidence-bundle-v1.schema.json` | resolution output |
| `schema/federation-run-v1.schema.json` | reproducible run identity + independence |
| `schema/federation-edge-record-v1.schema.json` | descriptive producer/consumer edge |
| `conformance/` | validation and bounded reference inference |
| `adapters/` | opt-in cross-project resolution adapters |
| `CONTRIBUTING.md` | evidence and contribution discipline |

## Design principles

1. Separate properties and preserve foreign native claims.
2. Resolve claims to immutable evidence.
3. Declare scope, trust assumptions and explicit non-claims.
4. Treat missing evidence conservatively.
5. Record disagreement rather than normalizing it away.
6. Verification is not endorsement.
7. Mapping, listing and a technical pilot do not establish Federation membership.

## Origin

The vocabulary emerged from execution-assurance work in [REMORA-research](https://github.com/darklordVirtual/REMORA-research) and cross-system review. It is deliberately separated from any one implementation so the methodology can be challenged and applied independently.

## Licence

Apache-2.0.
