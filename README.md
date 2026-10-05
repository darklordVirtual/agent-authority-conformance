# Agent Authority Conformance Profiles (AACP)

> **Evidence before adjectives.** A vendor-neutral vocabulary for evaluating authority and execution controls in agentic systems.

> **Project identity:** this repository is independent. It is not the LF Decentralized Trust *Agent Authority Conformance* lab and not `Agent-Authority-Conformance/aps-conformance-suite`; it is not a Federation authority, and not a membership or certification body. The project was published as "Agent Authority Conformance" until 2026-10 and gave that name up because the lab holds it; see [TERMINOLOGY.md](TERMINOLOGY.md#names).

**Status:** Draft v0.2 (opt-in; v0.1 preserved) · Run protocol v0.3 (draft) · **No aggregate score** · **Not a certification** · **Not a product ranking**

When an agent runtime says *“the tool call was authorized”*, that statement hides several independent security and governance questions. AACP separates those questions so implementations can state precisely what they have demonstrated, what remains untested, and what they deliberately do not claim.

The project evaluates **evidence**, not marketing language. Profiles are the unit: one bounded property an implementation can try to demonstrate, with fixtures that would fail it. Results are recorded with Bounded Claim Reproduction ([METHOD.md](METHOD.md)), which states who ran what against which revisions and what the result does not establish. The seven principles that bind both are in [CHARTER.md](CHARTER.md).

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

v0.2 records verification execution separately from the property result:

| Verification | Property status | Meaning |
|---|---|---|
| `NOT_RUN` | `UNTESTED` | No applicable verification completed. |
| `NOT_RUN` | `OUT_OF_SCOPE` | Explicit non-claim within the assessment scope. |
| `COMPLETED` | `PASS` / `FAIL` | Resolved evidence establishes the bounded property or its violation. |
| `COMPLETED` | `NOT_ESTABLISHED` | The procedure ran, but evidence supports neither conclusion. |
| `UNSUPPORTED` / `INVALID_INPUT` / `ERROR` | `null` | A non-verdict with a structured verifier error. |

A runtime success, valid receipt or passing test expectation is not a property
verdict. Missing evidence alone is never a demonstrated violation.

## Evidence tiers

- **RESOLVED** — the assessor inspected the named test, fixture, artifact or code at a stated revision.
- **REPORTED** — the evidence was described but not independently resolved to an artifact.
- **NONE** — no evidence was offered.

In v0.2, `PASS` and `FAIL` require nonempty, pinned `RESOLVED` evidence.
Resolving an artifact does not alone prove that it is sufficient.

## One rule matters most

**Do not aggregate A–G into a score.**

No percentage, star rating, “5/7 conformant”, security grade or ranking is valid under this model. The properties are not commensurable and deployment priorities differ.

## Repository map

| Path | Purpose |
|---|---|
| [`CHARTER.md`](CHARTER.md) | The seven principles, including implementation neutrality |
| [`METHOD.md`](METHOD.md) | Bounded Claim Reproduction: the chain, levels BCR-0 to BCR-4, result vocabulary |
| [`TERMINOLOGY.md`](TERMINOLOGY.md) | Names, the four distinctions (conformance, interoperability, validation, certification), properties A to G, profile identity |
| [`GOVERNANCE.md`](GOVERNANCE.md) | How profiles and runs are proposed, frozen and reviewed |
| [`SPECIFICATION-v0.2.md`](SPECIFICATION-v0.2.md) | Draft v0.2 semantics and bounded E evidence rules |
| [`RUN-PROTOCOL-v0.3.md`](RUN-PROTOCOL-v0.3.md) | Private-first runs against other projects' pinned artifacts |
| [`docs/FEDERATION-TRACKS.md`](docs/FEDERATION-TRACKS.md) | Optional self-service (producer offer) and manual tracks; `aacp next`, map export |
| [`conformance/lab/`](conformance/lab/) | `python -m conformance.lab`: scope, freeze, run, package, share, rerun |
| [`schema/lab/`](schema/lab/) | Run scope, consent, fault and result schemas |
| [`templates/scopes/`](templates/scopes/) | Draft scopes for external targets (not runnable until agreed) |
| [`schema/assessment-v0.2.schema.json`](schema/assessment-v0.2.schema.json) | Opt-in v0.2 assessment schema |
| [`MIGRATION-v0.2.md`](MIGRATION-v0.2.md) | Per-record migration and compatibility rules |
| [`SPECIFICATION.md`](SPECIFICATION.md) | Preserved normative v0.1 specification |
| [`schema/assessment.schema.json`](schema/assessment.schema.json) | Preserved v0.1 schema |
| [`examples/`](examples/) | Versioned examples and historical assessments |
| [`conformance/`](conformance/) | Validation and bounded E reference inference |\n| [`aacp/adversarial.py`](aacp/adversarial.py) | Portable vendor-neutral C/F/G adversarial self-service runner |\n| [`docs/ADVERSARIAL-SELF-SERVICE.md`](docs/ADVERSARIAL-SELF-SERVICE.md) | Adapter contract, claim ceilings and local self-run workflow |
| [`conformance/mutations-v0.2.json`](conformance/mutations-v0.2.json) | Seeded faults for the E rule; `python -m conformance.mutations` scores the fixtures against them |
| [`conformance/invariants.py`](conformance/invariants.py) | Metamorphic relations and a differential reference model for the E rule over a generated space |
| [`conformance/coverage.py`](conformance/coverage.py) | Strict, score-free A–G component matrix for cross-platform assessment comparison |
| [`MUTATIONS-AND-INVARIANTS.md`](MUTATIONS-AND-INVARIANTS.md) | What the two adequacy checks establish, and what they do not |
| [`tests/fixtures/`](tests/fixtures/) | Synthetic, committed evidence-sufficiency cases |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Evidence and contribution discipline |

## Quick start

For producer, consumer, verifier or reproduction work, start with
[the self-service interop guide](docs/INTEROP-SELF-SERVICE.md). AI agents enter
through [AGENTS.md](AGENTS.md). The **Federation self-service** GitHub Action
resolves committed adapters and prepares hash-bound run evidence, with result
details and uploads gated by the frozen publication policy.

Python 3.12 or newer:

```sh
python -m venv .venv
# Linux/macOS: . .venv/bin/activate
# Windows PowerShell: .venv/Scripts/Activate.ps1
python -m pip install -r requirements-dev.txt
python -m conformance.check
python -m conformance.mutations
python -m conformance.invariants
python -m conformance.coverage tests/adversarial/assessment-pass.json
aacp adversarial --list
aacp adversarial --adapter ./aacp_adapter.py:run_case --require-supported
python -m unittest discover -s tests -v
```

Activate the environment with the command for your platform before installing.
For the first installer-backed self-service commands (`aacp init`, `validate`
and `inspect`, each with `--json`), see
[CLI onboarding](docs/CLI-ONBOARDING.md). They validate project configuration
and inspect local pins only; they do not award property verdicts.
The checks run offline after dependency installation and do not invoke external
tools or regenerate committed expectations. `mutations` seeds faults into the
E rule in memory and asks whether the fixtures notice; `invariants` checks
relations that need no expected answer over a generated input space. Both are
read-only; see [MUTATIONS-AND-INVARIANTS.md](MUTATIONS-AND-INVARIANTS.md).

For cross-platform runs, export each platform's assessment in the v0.2 format
and pass the files to `python -m conformance.coverage`. The command requires
one explicit row for every REMORA core component A–G and emits only a
component matrix. It never computes a score, ranks platforms, or upgrades
self-reported evidence.

The E reference rule consumes **already accepted evidence**. It does not verify
artifacts, inspect credential custody or establish coverage itself. Its synthetic
fixtures test inference semantics, not the security of a deployed product.
See [the input trust boundary](SPECIFICATION-v0.2.md#6-bounded-reference-rule-and-corpus).

The portable adversarial command is a **local SELF_RUN**, not a Federation self-service run: it may execute the subject maintainer's own adapter and emits no independence credit. Federation self-service remains runner-owned and does not execute producer code. See [Portable adversarial self-service](docs/ADVERSARIAL-SELF-SERVICE.md).\n\n## Running a pilot against another project

The v0.3 run protocol turns an agreed, bounded question about another project's
artifacts into a package that the other maintainers review privately before
anything is published, and that anyone can rerun.

```sh
python -m conformance.lab init my-run --kind verification   # or --kind adequacy, or --template
# complete runs/my-run/SCOPE.json with the other party, then:
python -m conformance.lab pin my-run
python -m conformance.lab consent my-run --who <handle> --action scope_agreed --ref <comment URL>
python -m conformance.lab consent my-run --who <handle> --action run_authorized --ref <comment URL>
python -m conformance.lab freeze my-run                     # prints the plan hash: publish it first
python -m conformance.lab freeze my-run --published-ref <URL>
python -m conformance.lab run my-run
python -m conformance.lab package my-run
python -m conformance.lab share my-run --invite <handle> ... # private repo in R-research-lab
python -m conformance.lab review my-run --who <handle> --classification <URL>
python -m conformance.lab publish my-run                    # only after every approver approved
python -m conformance.lab rerun runs/my-run                 # or: python3 rerun.py inside a package
```

Two run kinds share one lifecycle:

- **verification** reports one result per input and claim, `ESTABLISHED`,
  `CONTRADICTED` or `NOT_ESTABLISHED`, from the runner's own implementation;
- **adequacy** seeds agreed faults into the other party's checker and reports
  which ones the corpus distinguishes, with mandatory positive and inert
  controls.

Each run carries an independence label (`SELF_RUN`, `SECOND_IMPLEMENTATION`,
`INDEPENDENT_IMPLEMENTATION`) and a claim ceiling. There is still no aggregate:
nothing is summed across rows, fault sets or claims. Consent is an append-only,
hash-chained log; publication needs every named approver; an unreleased report
is not citable. `runs/` is gitignored, and the delivery repositories live in
the `R-research-lab` organisation set in [`lab.toml`](lab.toml). See
[RUN-PROTOCOL-v0.3.md](RUN-PROTOCOL-v0.3.md).

## Minimal assessment shape

This complete, schema-valid v0.2 skeleton intentionally grants no conformance
credit. It is also committed as [`examples/v0.2/minimal.json`](examples/v0.2/minimal.json).

```json
{
  "assessed_at": "2026-09-15",
  "properties": [
    {
      "caveat": "This is a valid assessment skeleton and grants no conformance credit.",
      "evidence": [],
      "evidence_tier": "NONE",
      "id": "C",
      "property": "Exact-Call Integrity",
      "reasoning": "No verification procedure has been run for this example.",
      "status": "UNTESTED",
      "verification_status": "NOT_RUN"
    }
  ],
  "revision": "not-assessed",
  "scope": {
    "explicit_non_claims": [],
    "external_effects": "none",
    "process_model": "not-assessed",
    "trust_assumptions": []
  },
  "spec_version": "0.2",
  "system": "Example Runtime (unassessed)",
  "system_version": "not-assessed"
}
```

The schema intentionally contains **no aggregate score field**. Schema validation
checks report structure; the assessor remains responsible for the evidence.

## Design principles

1. **Separate properties.** Receipt correctness is not authority provenance; exact binding is not semantic correctness; dispatch success is not effect verification.
2. **Resolve claims to immutable evidence.** Prefer test path + revision + command over README prose.
3. **Declare scope.** Process model, deployment assumptions, simulated vs real effects and explicit non-claims belong in the assessment.
4. **Treat missing evidence conservatively.** Distinguish `UNTESTED` from completed-but-inconclusive `NOT_ESTABLISHED`; neither is a demonstrated violation.
5. **Record disagreement.** An implementer should be able to see exactly where an assessor's interpretation differs from their own claim.

## Origin

The vocabulary emerged from execution-assurance work in [REMORA-research](https://github.com/darklordVirtual/REMORA-research) and a cross-system dialogue around AEGIS Core. This repository deliberately separates the conformance model from any one implementation so the methodology can be challenged, reproduced and applied independently.

The success criterion is simple: an implementer should be able to read an assessment and say, *“yes, this describes exactly what we proved, what we did not prove, and what we are not trying to solve.”*

## Standards discussion

The v0.2 evidence-sufficiency distinction is informed by
[CoSAI/OASIS WS4 RFC #189](https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/issues/189),
where contributions by `@darklordVirtual` address verifier semantics and the
separation of evidence inputs from test expectations. This repository is an
independent draft; the link does not imply CoSAI adoption or endorsement.

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
