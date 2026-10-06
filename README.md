# Agent Authority Conformance Profiles (AACP)

> **Evidence before adjectives.** A vendor-neutral vocabulary for stating what an agent runtime has proven about authority and execution control, and what it has not.

**Status:** Draft v0.2 (opt-in; v0.1 preserved) · Run protocol v0.3 (draft) · No aggregate score · Not a certification · Not a ranking

AACP is independent. It is not the LF Decentralized Trust *Agent Authority Conformance* lab, not a Federation authority and not a certification body. See [TERMINOLOGY.md](TERMINOLOGY.md#names).

## Why

*"The tool call was authorized"* bundles several independent questions. AACP separates them into seven properties, so an implementation can state exactly what it has demonstrated, what remains untested and what it deliberately does not claim. Each claim resolves to pinned evidence at a stated revision, and every result carries a claim ceiling.

Profiles are the unit of work: one bounded property with fixtures that would fail it. Results are recorded with Bounded Claim Reproduction ([METHOD.md](METHOD.md)): who ran what, against which bytes, and what the result does not establish. Governing principles: [CHARTER.md](CHARTER.md).

## The seven properties

| ID | Property | Core question |
|---|---|---|
| **A** | Receipt Integrity | Is the authorization artifact authentic, unmodified, valid and replay-bounded? |
| **B** | Authority Provenance | Who or what had authority to approve the action? |
| **C** | Exact-Call Integrity | Is authorization bound to the exact call that executes? |
| **D** | Semantic Authority | Was the action permitted in its real operational meaning? |
| **E** | Execution-Boundary Integrity | Can the protected effect be reached only through the governed path? |
| **F** | TOCTOU Resistance | Can approved conditions change between authorization and execution? |
| **G** | Effect Verification | Is the actual external effect verified after execution? |

Properties are separable. Evidence for one grants no credit in another, and **A–G are never aggregated** into a score, percentage, grade or ranking.

## Results

| Verification | Property status | Meaning |
|---|---|---|
| `NOT_RUN` | `UNTESTED` | No applicable verification completed. |
| `NOT_RUN` | `OUT_OF_SCOPE` | Explicit non-claim within the assessment scope. |
| `COMPLETED` | `PASS` / `FAIL` | Resolved evidence establishes the bounded property or its violation. |
| `COMPLETED` | `NOT_ESTABLISHED` | The procedure ran; evidence supports neither conclusion. |
| `UNSUPPORTED` / `INVALID_INPUT` / `ERROR` | `null` | Non-verdict with a structured verifier error. |

Evidence tiers are `RESOLVED` (inspected at a stated revision), `REPORTED` (described, not resolved) and `NONE`. In v0.2, `PASS` and `FAIL` require pinned `RESOLVED` evidence. A runtime success, valid receipt or passing test is not a property verdict, and missing evidence is never a demonstrated violation.

## Quick start

Python 3.12 or newer:

```sh
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m conformance.check
python -m conformance.mutations
python -m conformance.invariants
python -m unittest discover -s tests -v
```

All checks run offline, are read-only and never regenerate committed expectations.

| Task | Start here |
|---|---|
| Producer, consumer, verifier or reproduction work | [Interop self-service guide](docs/INTEROP-SELF-SERVICE.md) |
| AI agents | [AGENTS.md](AGENTS.md) |
| Project onboarding (`aacp init`, `validate`, `inspect`) | [CLI onboarding](docs/CLI-ONBOARDING.md) |
| Local C/F/G adversarial probes (`aacp adversarial`) | [Adversarial self-service](docs/ADVERSARIAL-SELF-SERVICE.md) |
| Runs against another project's pinned artifacts | [Federation tracks](docs/FEDERATION-TRACKS.md), [RUN-PROTOCOL-v0.3.md](RUN-PROTOCOL-v0.3.md) |
| Cross-implementation comparison | `python -m conformance.coverage <assessment.json> ...` |

`aacp adversarial` is a local `SELF_RUN`: it executes the maintainer's own adapter and carries no independence credit. `conformance.coverage` emits a component matrix with one explicit row per property; it never scores, ranks or upgrades self-reported evidence.

## Runs against other projects

The v0.3 run protocol turns an agreed, bounded question about another project's artifacts into a package that the other maintainers review privately before publication, and that anyone can rerun.

```sh
python -m conformance.lab init my-run --kind verification   # or --kind adequacy
python -m conformance.lab pin my-run
python -m conformance.lab consent my-run --who <handle> --action scope_agreed --ref <URL>
python -m conformance.lab freeze my-run
python -m conformance.lab run my-run
python -m conformance.lab package my-run
python -m conformance.lab publish my-run                    # only after every approver approved
python -m conformance.lab rerun runs/my-run
```

- **verification** reports `ESTABLISHED`, `CONTRADICTED` or `NOT_ESTABLISHED` per input and claim;
- **adequacy** seeds agreed faults into the other party's checker and reports which the corpus distinguishes, with positive and inert controls.

Every run carries an independence label (`SELF_RUN`, `SECOND_IMPLEMENTATION`, `INDEPENDENT_IMPLEMENTATION`) and a claim ceiling. Consent is an append-only, hash-chained log, publication requires every named approver, and an unreleased report is not citable.

## Trust boundary

The reference rules consume **already accepted evidence**. They do not authenticate artifacts, inspect credential custody or establish coverage. A hash establishes byte identity, not authenticity, execution or independence. Synthetic fixtures test inference semantics, not the security of a deployed product. See [SPECIFICATION-v0.2.md §6](SPECIFICATION-v0.2.md#6-bounded-reference-rule-and-corpus).

## Repository map

| Path | Purpose |
|---|---|
| [`CHARTER.md`](CHARTER.md) · [`METHOD.md`](METHOD.md) · [`TERMINOLOGY.md`](TERMINOLOGY.md) · [`GOVERNANCE.md`](GOVERNANCE.md) | Principles, Bounded Claim Reproduction, vocabulary, governance |
| [`SPECIFICATION-v0.2.md`](SPECIFICATION-v0.2.md) · [`MIGRATION-v0.2.md`](MIGRATION-v0.2.md) | Draft v0.2 semantics and migration rules |
| [`SPECIFICATION.md`](SPECIFICATION.md) · [`schema/assessment.schema.json`](schema/assessment.schema.json) | Preserved v0.1 specification and schema |
| [`schema/`](schema/) | Assessment, adapter, run and lab schemas |
| [`profiles/`](profiles/) | Bounded, implementation-neutral reproduction profiles |
| [`adapters/`](adapters/) | Committed, hash-pinned adapters for public artifacts |
| [`conformance/`](conformance/) | Validation, reference inference, mutations, invariants, coverage |
| [`conformance/lab/`](conformance/lab/) | Run protocol: scope, pin, consent, freeze, run, package, rerun |
| [`aacp/`](aacp/) | Installable CLI |
| [`examples/`](examples/) · [`tests/fixtures/`](tests/fixtures/) | Examples and synthetic evidence cases |
| [`MUTATIONS-AND-INVARIANTS.md`](MUTATIONS-AND-INVARIANTS.md) | What the adequacy checks establish, and what they do not |

## Minimal assessment

A schema-valid v0.2 skeleton that grants no credit, also committed as [`examples/v0.2/minimal.json`](examples/v0.2/minimal.json). The schema has no aggregate score field.

```json
{
  "spec_version": "0.2",
  "system": "Example Runtime (unassessed)",
  "system_version": "not-assessed",
  "revision": "not-assessed",
  "assessed_at": "2026-09-15",
  "scope": {
    "process_model": "not-assessed",
    "external_effects": "none",
    "trust_assumptions": [],
    "explicit_non_claims": []
  },
  "properties": [
    {
      "id": "C",
      "property": "Exact-Call Integrity",
      "status": "UNTESTED",
      "verification_status": "NOT_RUN",
      "evidence_tier": "NONE",
      "reasoning": "No verification procedure has been run for this example.",
      "caveat": "This is a valid assessment skeleton and grants no conformance credit.",
      "evidence": []
    }
  ]
}
```

## Standards context

The v0.2 evidence-sufficiency distinction is informed by [CoSAI/OASIS WS4 RFC #189](https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/issues/189). The link does not imply CoSAI adoption or endorsement.

## Contributing

The most useful contributions sharpen boundaries rather than broaden claims: adversarial examples showing two properties are not separable, reproducible fixtures, assessments of unrelated runtimes, evidence that a definition favours one architecture, and dimensions A–G cannot represent. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Apache-2.0. Contributions are accepted under the same terms.
