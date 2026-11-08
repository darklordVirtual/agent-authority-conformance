# AACP controls

AACP controls turn security findings into repeatable, comparable checks. A
**control** names one weakness and the A-G property it bears on. A **binding**
implements probes for that control against one pinned subject. A **run**
executes the binding, and a **report** derives an A-G assessment from the run.
The same catalog applies to every project; only the binding is project-specific.

```text
controls/aacp-controls-v1/catalog.json      project-neutral controls and probe contracts
controls/bindings/<id>/binding.json         subject pin, probes, repairs, scope (implementation)
controls/bindings/<id>/expected.json        expected outcome per probe, written before the run
controls/bindings/<id>/tests/...            probe code installed into the subject
reports/<id>/results/<run>.json             result records, never overwritten
reports/<id>/CURRENT                        the result the committed report is generated from
reports/<id>/REPORT.md, examples/<id>.json  generated report and assessment (schema v0.1)
```

## Semantics

A probe **observes** a weakness when it reproduces it on the pristine subject.
A probe with a declared **repair** (a mutation applied alone to a pinned file)
**discriminates** when the repaired subject no longer shows the weakness. A
probe that would pass whether or not the weakness exists tests nothing
(SPECIFICATION §5), so discrimination is required for any status.

| Probe result | Meaning |
| :--- | :--- |
| `OBSERVED` | weakness reproduced on the pristine subject |
| `NOT_OBSERVED` | probe ran, weakness not reproduced. **Not a PASS.** |
| `NOT_APPLICABLE` | binding declares the subject has no such mechanism, with a reason |
| `NON_VERDICT` | pin, bytes, region, build or harness failure |

A property row is `FAIL` only when at least one probe is **executed**
(`cargo-test` or `command`), has an **`exact`** relationship to that property,
is `OBSERVED` and `DISCRIMINATES`. Static (`source-check`) probes, `structural`
or `partial` relationships and controls outside A-G are reported, never
counted. A property is `OUT_OF_SCOPE` only when the binding records the
implementer's own non-claim. Otherwise it is `UNTESTED`. **Controls never
yield `PASS`**: a few probes failing to find a weakness are not direct
evidence that a property holds.

## Probe kinds

All three kinds are generic. A non-Rust project uses `command` and `source-check`.

| Kind | Observed when | Fields |
| :--- | :--- | :--- |
| `cargo-test` | the named test in the binding's installed test target passes | `test`; binding `runners.cargo` gives `crate`, `test_target`, `install`, `rust_toolchain` |
| `command` | `argv` exits 0 in `cwd` (pytest, go test, npm test, a script) | `argv`, optional `cwd` |
| `source-check` | every predicate holds | `predicates` |

Source-check predicates: `matches` and `not_matches` (regex, optionally within a
`region` from `start` to `end` markers), `order` (`then` occurs after `first`),
`json_equals` (`value`, or `value_sha256_of` a literal), `json_lacks`
(`path` may map lists with `name[]`), `json_exists`, `json_ne_head` (value
differs from the checked-out commit). A missing file, region or marker is a
`NON_VERDICT`, never a silent pass or fail.

Every subject file a repair touches must be pinned by SHA-256 in
`subject.files`. Repairs need a unique anchor; otherwise `ANCHOR_ERROR`. A
repaired subject that does not build is `BUILD_ERROR`, never discrimination.
The runner restores every pinned file and removes installed probes, then
re-verifies the pins.

## Normative basis

A weakness is not automatically a failure of every nearby property. Every A-G
control therefore carries a `normative_basis`: the SPECIFICATION §2 text it
relies on, the rationale for why the weakness defeats that property, and a
**boundary** stating when the control does not establish a failure (for
example, call binding enforced elsewhere on the mandatory path, or a
declared bearer design). A control without one is rejected. The report
prints the basis for every counted control and puts the boundary in the
row's caveat, so an implementer can contest the mapping, not just the probe.

## Probe contracts

Each catalog control has a `probe_contract`: setup, stimulus, observation and
repair. A binding for another project must implement that contract in the
project's own API. Results for the same control are comparable across
projects only to the extent the contract is followed, so a binding states
deviations in the probe `description`.

## Running

```sh
python -m conformance.controls run --binding controls/bindings/<id> --subject <checkout> \
    --out reports/<id>/results/<run>.json --run-id <run> --operator "<who>" --independence AUTHOR_RUN
python -m conformance.controls report --binding controls/bindings/<id> \
    --result reports/<id>/results/<run>.json --assessment examples/<id>.json --markdown reports/<id>/REPORT.md
python -m conformance.controls compare <result-a.json> <result-b.json>
```

`run` executes subject code for executable probes: use a disposable environment
and an explicit execution agreement (AGENTS.md). Exit status 0 means every
probe matched `expected.json`. The `controls` workflow reruns every binding on a
clean runner as a `REPRODUCTION`, fails if the findings differ from the run
named in `CURRENT`, and fails if the regenerated report differs from the
committed one.

## Binding a new project

1. Copy `templates/controls-binding/` to `controls/bindings/<project>-<short-rev>/`.
2. Pin the revision and the SHA-256 of every file a repair or source check reads.
3. For each catalog control that applies, write a probe following its contract,
   and a minimal repair that removes the weakness. Mark a control
   `not_applicable` with a reason when the mechanism does not exist.
4. Write `expected.json` before running. Never edit it to match output; a
   changed expectation is a new run.
5. Run, commit the result under `reports/<id>/results/`, set `CURRENT`,
   generate the report, and send the draft to the implementer (SPECIFICATION §8).

A new control needs a catalog entry with a probe contract and at least one
binding whose probe discriminates. Changing a control's meaning is a new
catalog version.

## Limits

Probes and repairs are written by the assessor, so runs are `AUTHOR_RUN` or
`REPRODUCTION`, not independent implementations. A binding exercises the
subject's API as the assessor understands it; the implementer may disagree
with a probe's fidelity, which is recorded rather than normalized away.
Static probes read source text and can be defeated by refactoring without any
change in behaviour.
