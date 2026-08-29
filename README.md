# Agent Authority Conformance

> **Evidence before adjectives.** A vendor-neutral vocabulary for evaluating authority and execution controls in agentic systems.

**Status:** Draft v0.1 · **No aggregate score** · **Not a certification** · **Not a product ranking**

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

## Assessment statuses

- **PASS** — direct, reproducible evidence supports the property within the declared scope.
- **UNTESTED** — available evidence does not demonstrate the property.
- **OUT OF SCOPE** — the implementer explicitly does not claim the property.
- **FAIL** — reproducible evidence shows the property does not hold under a tested condition.

`OUT OF SCOPE` is not a deficiency. Narrow, explicit claims are preferable to broad, weak ones.

## Evidence tiers

- **RESOLVED** — the assessor inspected the named test, fixture, artifact or code at a stated revision.
- **REPORTED** — the evidence was described but not independently resolved to an artifact.
- **NONE** — no evidence was offered.

A `PASS` requires `RESOLVED` evidence.

## One rule matters most

**Do not aggregate A–G into a score.**

No percentage, star rating, “5/7 conformant”, security grade or ranking is valid under this model. The properties are not commensurable and deployment priorities differ.

## Repository map

| Path | Purpose |
|---|---|
| [`SPECIFICATION.md`](SPECIFICATION.md) | Normative v0.1 property definitions, statuses and evidence rules |
| [`schema/assessment.schema.json`](schema/assessment.schema.json) | Machine-readable assessment format |
| [`examples/`](examples/) | Bounded example assessments with explicit scope and caveats |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to propose property, evidence and assessment changes |

## Minimal assessment shape

```json
{
  "spec_version": "0.1",
  "system": "Example Runtime",
  "system_version": "1.0.0",
  "revision": "immutable-revision",
  "scope": {
    "process_model": "single-process",
    "external_effects": "simulated",
    "explicit_non_claims": ["multiprocess exactly-once effects"]
  },
  "properties": [
    {
      "id": "C",
      "status": "PASS",
      "evidence_tier": "RESOLVED",
      "supported_scope": "full argument binding at dispatch",
      "caveat": "No evidence for cross-process execution",
      "evidence": []
    }
  ]
}
```

The schema intentionally contains **no aggregate score field**.

## Design principles

1. **Separate properties.** Receipt correctness is not authority provenance; exact binding is not semantic correctness; dispatch success is not effect verification.
2. **Resolve claims to immutable evidence.** Prefer test path + revision + command over README prose.
3. **Declare scope.** Process model, deployment assumptions, simulated vs real effects and explicit non-claims belong in the assessment.
4. **Treat missing evidence conservatively.** Absence of evidence is `UNTESTED`, never `FAIL`.
5. **Record disagreement.** An implementer should be able to see exactly where an assessor's interpretation differs from their own claim.

## Origin

The vocabulary emerged from execution-assurance work in [REMORA-research](https://github.com/darklordVirtual/REMORA-research) and a cross-system dialogue around AEGIS Core. This repository deliberately separates the conformance model from any one implementation so the methodology can be challenged, reproduced and applied independently.

The success criterion is simple: an implementer should be able to read an assessment and say, *“yes, this describes exactly what we proved, what we did not prove, and what we are not trying to solve.”*

## Contributing

The most valuable contributions are not new adjectives or broader claims. They are:

- adversarial examples that show two properties are not actually separable,
- reproducible fixtures that sharpen a property boundary,
- assessments of unrelated runtimes,
- evidence that a definition is biased toward one architecture,
- proposals for missing dimensions that cannot be represented by A–G.

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

Apache-2.0. A vocabulary nobody may lawfully reuse is not vendor-neutral, and
the repository shipped without a licence file until 2026-08-29. Contributions
are accepted under the same terms.
