# Cross-project run protocol and lab tooling (v0.3) — design

**Date:** 2026-09-30
**Status:** design, awaiting maintainer review
**Branch:** `feat/v0.3-run-protocol`

## 1. Purpose

Agent Authority Conformance (AAC) currently defines a vocabulary (A–G), an
evidence-sufficiency distinction (v0.2) and a bounded E reference rule. It has
no way to *run* a bounded test against another project's artifacts and deliver
the result under the rules agreed in
[aeoess/agent-governance-vocabulary#177](https://github.com/aeoess/agent-governance-vocabulary/issues/177).

This design adds a **run protocol** and **lab tooling** so that AAC can:

1. run a scoped test against another project's pinned artifacts;
2. package the result like
   [`corpus-adequacy/remora-es-v11-adequacy`](https://github.com/corpus-adequacy/remora-es-v11-adequacy):
   frozen plan, pinned inputs, controls, manifest, reproduction instructions,
   attribution;
3. deliver it first in a **private repository** that the other maintainer(s)
   review before anything is published;
4. let anyone, including the other maintainer, **rerun** it from a fresh copy
   and get a structured reproduced/diverged answer.

Success criterion: the other party can read the package and say *"this is
exactly what was pinned, what was checked, what it establishes, and what it
does not"*, rerun it with one command, and control whether it is published.

## 2. Principles enforced by the tooling

The following positions from #177 and REMORA-research#629 are enforced by the
tool, not only stated in prose. The shared principles text is owned by the
common layer (aeoess' proposed `PRINCIPLES.md`); AAC links to it and does not
copy it.

| # | Rule | Enforcement |
|---|---|---|
| P1 | Inputs are pinned by commit and per-file SHA-256. | `freeze` fetches and hashes; `run` and `rerun` refuse on mismatch. |
| P2 | The run plan is frozen and its hash published **before** execution. | `run` requires a `published_ref` for the plan hash. |
| P3 | Results are per claim; no aggregate verdict or score. | Schemas reject `overall`, `score`, `total`, `aggregate`; no cross-row sums in reports. |
| P4 | A crash or missing result is never counted as a finding. | `killed_crash` and `execution: ERROR` are separate categories. |
| P5 | Positive and inert controls are mandatory for adequacy runs. Verification runs compare against the producer's published expected outcomes only after results are written, and report agreement separately. | Unkilled positive → `VOID_NO_SCORE`; changed inert → `VOID`. Expected outcomes are never passed to the verifier; agreement is a separate table, not a result. |
| P6 | Each run states a claim ceiling. | `SCOPE.json` requires nonempty `establishes` and `does_not_establish`. |
| P7 | Attribution and licence travel with the work. | `NOTICE` generated from `subjects[].license/attribution`; upstream licence text copied. |
| P8 | Private first; every named approver approves publication separately. | `publish` requires `publication_approved` from all approvers. |
| P9 | An unreleased report is not citable. | `WITHHELD` state; `STATUS.md` banner. |
| P10 | Verification is not endorsement; independence is labelled honestly. | Mandatory `independence` field printed at the top of `REPORT.md`. |
| P11 | Known and held-out faults are reported separately; denominators are never reduced after seeing results. | Separate tables; fault files are frozen by hash. |
| P12 | Earlier results are never overwritten. | A new commit is a follow-up run with its own plan, linked to the previous one. |
| P13 | Joining one pilot creates no obligation to join another. | No cross-run state; each run has its own scope and consent log. |

## 3. Decisions taken during design

- **Two run kinds, one framework.** `verification` (our own implementation
  reports per claim over pinned artifacts) and `adequacy` (seeded faults in
  the other party's checker; does their corpus distinguish them).
- **Mutation engines behind an interface.** A native stdlib engine and an
  adapter to pinned [corpus-adequacy](https://github.com/corpus-adequacy/corpus-adequacy);
  optional cross-check between them.
- **Private repositories live in a dedicated GitHub organisation** so that
  invitations can be read-only. The organisation is set in `lab.toml`
  (`org = "…"`) or with `--org`; there is no built-in default in code. The
  maintainer's preferred name `R-research` is already taken on GitHub by an
  unrelated user account (`r-research`, checked 2026-09-30), so the
  organisation name must be chosen before step 6 of §12 can be shared.
  `share` verifies that the target owner is an organisation (not a user) and
  refuses otherwise, since user-owned repositories cannot grant read-only
  invitations.
- **First reference run** is a `SELF_RUN` against REMORA-research
  evidence-sufficiency v1.2, plus a synthetic verification demo. External
  targets get scope templates only; nothing runs against another project
  before its scope is agreed.
- **Architecture:** lab module in this repository; each run is a
  self-contained generated directory that becomes the private repository.
  An optional GitHub Actions rerun workflow is included, but local execution
  is normative.

## 4. Architecture

```
conformance/lab/
  __main__.py         CLI: python -m conformance.lab <command>
  canonical.py        canonical JSON (sorted keys, UTF-8, "\n"), sha256 helpers
  state.py            STATE.json lifecycle and transition guard
  scope.py            SCOPE.json load + structural validation
  consent.py          CONSENT.json append-only log and gate queries
  pins.py             fetch subject at commit, verify per-file sha256, read-only copy
  plan.py             RUN-PLAN-FROZEN.json, plan hash, fault-file hashes
  kinds/
    verification.py   claim registry; per-claim result records
    adequacy.py       rows × faults via an engine; controls; row status
  engines/
    base.py           Engine interface
    native.py         stdlib anchor/replacement engine, subprocess adapter
    corpus_adequacy.py adapter to pinned corpus-adequacy
  package.py          REPORT.md, MANIFEST.json, REPRODUCE.md, NOTICE, STATUS.md, rerun.py
  github.py           gh wrapper: private repo, read-only invites, visibility checks
  rerun.py            fresh fetch → verify → run → structured diff
schema/lab/           JSON Schemas for SCOPE, CONSENT, STATE, plan, results, faults
runs/<run_id>/        one directory per run (becomes the private repository)
templates/scopes/     scope templates for external targets (not runnable until agreed)
```

**Dependency rule.** `conformance/lab/` uses the Python standard library only
(Python ≥ 3.12), because it is vendored into every run package and must rerun
without installation. The JSON Schemas in `schema/lab/` are normative
documentation and are validated with `jsonschema` in this repository's tests;
at runtime the lab performs equivalent structural checks in stdlib code. A
test asserts the two agree on the committed fixtures.

The existing `conformance/` v0.1/v0.2 code is not modified.

## 5. Lifecycle

`STATE.json` holds the current state and a history of transitions. Each
command checks the state first and refuses illegal transitions (exit 2).

```
SCOPED ──freeze──▶ FROZEN ──run──▶ RUN ──package──▶ PACKAGED ──share──▶ SHARED_PRIVATE
                                                                          │
                                                               review ────┤
                                                                          ▼
                                                                       REVIEWED
                                                                  publish │ withhold
                                                                          ▼
                                                              PUBLISHED | WITHHELD
```

| Command | Requires | Effect |
|---|---|---|
| `init <run_id> --kind K [--template T] [--follow-up PREV --commit C]` | — | Create `runs/<run_id>/` with draft `SCOPE.json`, empty `CONSENT.json`, `STATE=SCOPED`. Follow-up inherits faults and controls, links `previous_run`. |
| `consent add --who --action --ref` | — | Append an event. `--ref` (URL of the comment where the person said it) is mandatory. |
| `freeze [--published-ref URL]` | `scope_agreed` and `run_authorized` from every approver | Fetch subjects, verify hashes, write `RUN-PLAN-FROZEN.json`, print plan hash. Without `--published-ref` the state stays `SCOPED` with a pending plan; re-invoking with the URL where the hash was published moves to `FROZEN`. |
| `run` | `FROZEN` | Baseline check; execute rows sequentially; re-verify pinned bytes after each row. |
| `package` | `RUN` | Build the delivery package. |
| `share --org O --invite USER…` | `PACKAGED`, `lab.toml` or `--org`; `O` is an organisation | Create a **private** repository `O/<run_id>` via `gh`, verify visibility is private, push, invite each user with `pull` permission. |
| `review --corrections REF` / `--classification REF` | `SHARED_PRIVATE` | Record in `CONSENT.json`; corrections are appended as an addendum in `REVIEW.md`; measured values are never edited. |
| `publish` | `REVIEWED`; `publication_approved` from **all** approvers; no `publication_declined` or `withdrawn` after it | Update `STATUS.md` in a separate commit, set repository public, verify visibility. |
| `withhold` | any `publication_declined` | Mark `WITHHELD`; `STATUS.md` states "not citable as public evidence". |
| `rerun <path-or-repo-url>` | — | See §8. |

Consent is required from the approvers named in `SCOPE.json`. For a
`SELF_RUN`, the approver list may be only the runner, and the report says so.

## 6. Data formats

All lab JSON is canonical (sorted keys, UTF-8, two-space indent, trailing
`"\n"`). Hashes are SHA-256 over the file bytes.

### 6.1 `SCOPE.json`

```json
{
  "lab_version": "0.3",
  "run_id": "remora-es-v12-adequacy",
  "kind": "adequacy",
  "agreement_ref": "https://github.com/darklordVirtual/REMORA-research/issues/629",
  "independence": "SELF_RUN",
  "runner": {"project": "Agent Authority Conformance", "maintainers": ["darklordVirtual"]},
  "subjects": [{
    "project": "REMORA-research",
    "maintainers": ["darklordVirtual"],
    "repo": "https://github.com/darklordVirtual/REMORA-research",
    "commit": "c1345b1f9e0f877454bf996b2160d533c5a9b16a",
    "paths": ["conformance/evidence-sufficiency-v1/", "conformance/evidence-sufficiency-v1.2/"],
    "files_sha256": {"conformance/evidence-sufficiency-v1/checker.py": "c4ca50ae…"},
    "license": "BUSL-1.1",
    "attribution": "REMORA-research, darklordVirtual"
  }],
  "claims": [{"id": "C1", "text": "…", "layer": "…", "reads_fields": ["status", "reason"]}],
  "rows": [{"id": "row1-verdict", "adapter": "adapter/case.py", "projection": ["status", "reason"],
            "fault_sets": ["faults/known.json"], "cases": "adapter/cases/"}],
  "controls": {"positive": "controls/positive.json", "inert": "controls/inert.json"},
  "engine": {"name": "native", "cross_check": "corpus_adequacy"},
  "claim_ceiling": {"establishes": ["…"], "does_not_establish": ["…"]},
  "publication": {"private_first": true, "approvers": ["darklordVirtual"], "unreleased_citable": false}
}
```

- `independence` ∈ `SELF_RUN`, `SECOND_IMPLEMENTATION`,
  `INDEPENDENT_IMPLEMENTATION`. `INDEPENDENT_IMPLEMENTATION` requires a
  `independence_statement` naming what was not imported.
- `kind: verification` uses `inputs` (pinned artifact files) and `claims`
  instead of `rows`/`controls`, and requires `reference_time` when any claim
  is temporal.
- Aggregate-like keys (`overall`, `score`, `total`, `aggregate`, `grade`) are
  rejected anywhere in the document.

### 6.2 Verification result record

One record per (input, claim) in `results/claims.json`:

```json
{"input": "payment-over-limit", "claim": "aps_cap_compliance",
 "execution": "COMPLETED", "result": "CONTRADICTED",
 "reads": ["execution.nativeValue"], "evidence": ["sha256:…"],
 "unresolved_obligations": []}
```

- `execution` ∈ `COMPLETED`, `INVALID_INPUT`, `UNSUPPORTED`, `ERROR`.
- `result` ∈ `ESTABLISHED`, `CONTRADICTED`, `NOT_ESTABLISHED` when
  `COMPLETED`, else `null` with a `verifier_error {code, message}`.
- `NOT_ESTABLISHED` requires a nonempty `unresolved_obligations`.
- `reads` must be a subset of the claim's `reads_fields` paths and is
  recorded as actually read.
- Mapping to v0.2 property rows: `ESTABLISHED`↔`PASS`,
  `CONTRADICTED`↔`FAIL`, `NOT_ESTABLISHED`↔`NOT_ESTABLISHED`; the v0.2
  evidence-tier rules still apply when a result is transcribed into an
  assessment.

### 6.3 Fault definitions

`faults/*.json`, frozen by hash in the plan:

```json
{"set": "known",
 "source": {"author": "Rul1an", "ref": "https://github.com/corpus-adequacy/remora-es-v11-adequacy/…"},
 "faults": [{"id": "F03", "class": "guard_removal", "file": "conformance/evidence-sufficiency-v1/checker.py",
             "anchor": "…", "replacement": "…", "targets_claim": "C2",
             "expected_distinguishing_inputs": ["E11"]}]}
```

- `set` ∈ `known`, `held_out`. A held-out set becomes `known` once disclosed;
  the report states this.
- At `freeze`: each anchor must occur exactly once in the pinned file, and the
  mutated file must parse (`ast.parse` for Python; other languages declare no
  parse check and the report says so).
- Faults with no pinned input expected to distinguish them are allowed and,
  if they survive, are labelled as corpus discrimination limits.

### 6.4 Adequacy row result

`results/<row>.json`: per mutant `outcome` ∈ `killed`, `killed_crash`,
`survived`, with the projection diff for `killed`. Row `status`:

- `MEASURED` — positive control killed and inert control unchanged;
- `VOID_NO_SCORE` — positive control not killed;
- `VOID` — inert control changed any projection.

Counts are reported per row and per fault set. There is no sum across rows,
across sets, or into a percentage headline. A survivor is described as "not
distinguished on the declared projection by this corpus", never as a checker
defect.

### 6.5 `CONSENT.json`

Append-only. Actions: `scope_agreed`, `run_authorized`, `factual_corrections`,
`survivor_classification`, `publication_approved`, `publication_declined`,
`withdrawn`. Every event has `at` (UTC), `who` (GitHub handle), `action`,
`ref` (URL). The tool refuses to rewrite or delete events; a hash chain
(`prev_sha256`) makes edits detectable.

### 6.6 Package files

| File | Content |
|---|---|
| `STATUS.md` | Banner: private / published / withheld; citable or not. |
| `REPORT.md` | Independence label, pins, claim ceiling, per-row / per-claim tables, controls, crash kills, known vs held-out, limitations, AI-assistance disclosure. |
| `SCOPE.json`, `CONSENT.json`, `STATE.json` | As above. |
| `RUN-PLAN-FROZEN.json` | Pins, tool identity, Python version, fault-file hashes, adapter hashes, row list. |
| `faults/`, `controls/`, `adapter/` | Exact definitions and adapters used. |
| `results/` | Row or claim results; engine-native reports kept alongside. |
| `MANIFEST.json` | sha256 and byte length of every package file. |
| `ORIGINAL-TO-DELIVERY.json` | Only if delivery copies differ from originals (e.g. local paths); both digests and the exact transformation. |
| `REPRODUCE.md`, `rerun.py`, `lab/` | Rerun instructions, entry point, vendored pinned lab code. |
| `NOTICE`, `UPSTREAM-LICENSE-*.txt` | Attribution and upstream licence texts for quoted or mutated material. |
| `.github/workflows/rerun.yml` | Optional `workflow_dispatch` rerun. |

No tokens, e-mail addresses or local absolute paths are written into a
package; `package` scans for them and refuses.

## 7. Engines

```python
class Engine:
    name: str
    def identity(self) -> dict: ...                 # name, version/commit, sha256 of tool files
    def baseline(self, tree, row) -> dict: ...      # input id -> projection
    def mutant(self, tree, row, fault) -> dict: ... # input id -> projection | CRASH marker
```

Classification is done by `kinds/adequacy.py`, not by the engine, so both
engines are scored identically.

- **native** — copies the pinned tree to a temporary directory, applies one
  anchor→replacement, runs the row adapter in a subprocess per case with a
  timeout, reads a JSON projection from stdout. A non-zero exit, timeout or
  unparsable output is a crash. Environment is minimal (`PYTHONDONTWRITEBYTECODE=1`,
  `-B`, no inherited `PYTHONPATH`).
- **corpus_adequacy** — requires a pinned corpus-adequacy checkout
  (default commit `5fa2ff587497b00ac684a767335b9068f7e520a6`, verified by
  sha256 before use). Generates its manifest from our fault and control
  files, runs it, translates its report into §6.4 and keeps the original
  report in `results/engine/`.
- **cross-check** (optional per run) — runs both engines on the same plan;
  any per-mutant disagreement is reported as an engine finding in its own
  section and never changes the subject's row result.

## 8. Rerun

`python3 rerun.py` inside a package (or `python -m conformance.lab rerun`):

1. Verify `MANIFEST.json` against the package bytes.
2. Fetch each subject at its pinned commit into a temporary directory
   (`git` over HTTPS; the only network step, before any execution);
   verify every `files_sha256`.
3. Recompute the plan hash and compare with `RUN-PLAN-FROZEN.json`.
4. Run all rows or claims with the recorded engine.
5. Compare structurally with `results/`.

Outcome:

- `REPRODUCED` — identical per mutant / per claim; exit 0.
- `DIVERGED` — per-item diff printed and written to `rerun-<utc>.json`; exit 1.
- `NOT_REPRODUCIBLE` — manifest, pin or plan mismatch, or a missing
  prerequisite; exit 2.

Python version and duration are logged; a different Python minor version is
a warning, not a failure. A rerun against a **different commit** is not a
rerun: it is `init --follow-up`, producing a new run and package that link to
the previous one.

## 9. Error handling

- Exit 2 (no result produced): state violation, missing consent, pin or
  hash mismatch, non-unique anchor, unparsable replacement, baseline not
  matching the subject's own expected outcomes, pinned bytes changed during
  a run, secret or path found during packaging.
- Exit 1: completed measurement with survivors, or a diverged rerun.
- Engine `ERROR` for a row is recorded as `execution: ERROR`; it is never
  counted as killed.
- `gh` failures in `share` or `publish` do not change state; commands are
  idempotent and safe to retry. `share` verifies private visibility before
  pushing; `publish` verifies public visibility after the switch.

## 10. Specification changes

Additive only; v0.1 and v0.2 are unchanged.

- `RUN-PROTOCOL-v0.3.md` (normative): roles (producer, runner, approver),
  independence labels, lifecycle and gates, result vocabulary and mapping to
  v0.2, controls and VOID rules, crash accounting, known vs held-out faults,
  private-first publication, non-citability of unreleased reports, follow-up
  runs, claim ceiling requirements. Links to the #177 principles.
- README: section "Running a pilot against another project".
- CONTRIBUTING: how to propose a run against your own project.
- CHANGELOG: 0.3 entry.
- CI: add `python -m unittest discover -s tests/lab`; keep `git diff --exit-code`.

## 11. Testing

All tests use `unittest` and run offline.

- State machine: every illegal transition is rejected.
- Consent: `freeze` without agreement fails; `publish` fails unless every
  approver approved; a later `publication_declined` or `withdrawn` blocks it;
  hash chain detects an edited event.
- Pins: one changed byte → exit 2; missing file → exit 2.
- Plan: non-unique anchor and unparsable replacement are rejected at freeze.
- Controls: unkilled positive → `VOID_NO_SCORE`; changed inert → `VOID`.
- Crashes: counted as `killed_crash`, separate from `killed`.
- Schemas: aggregate keys rejected; `NOT_ESTABLISHED` without obligations
  rejected; stdlib checks agree with `jsonschema` on committed fixtures.
- Rerun: `REPRODUCED`, `DIVERGED` and `NOT_REPRODUCIBLE` each exercised.
- GitHub: `share`/`publish` tested with a fake `gh` on `PATH`; tests never
  contact GitHub.
- End-to-end: `tests/lab/fixtures/toy-subject/` (small checker, small corpus,
  one known survivor, one crash-only kill) through native engine, package
  and rerun. The corpus-adequacy engine test runs only when a pinned
  checkout is provided via environment variable and is skipped otherwise.

## 12. Delivery order

1. `RUN-PROTOCOL-v0.3.md`, `schema/lab/`, lab core (canonical, state, scope,
   consent, pins, plan) with tests.
2. Native engine, adequacy kind, toy subject end-to-end.
3. Package, `rerun.py`, `share`/`publish`/`withhold` via `gh`.
4. corpus-adequacy engine adapter and cross-check.
5. Verification kind and a synthetic verification demo.
6. Reference run `runs/remora-es-v12-adequacy/`: `SELF_RUN`, pinned at
   `c1345b1f9e0f877454bf996b2160d533c5a9b16a`, reusing Rul1an's published
   v1.1 fault definitions as a `known` set with attribution. Run and
   packaged locally; **not shared** until the organisation name is chosen and
   the maintainer says so.
7. Scope templates for external targets (APS fixtures at `948f99b8`,
   AgentAvow tool-manifest-digest vectors at `4404df2c`), marked as drafts
   that cannot be frozen until `scope_agreed` is recorded.

## 13. Out of scope

- Automatic posting to issues or pull requests.
- Any run against another project's artifacts before its scope is agreed.
- Package signing (DSSE or similar); may follow later.
- OS-level network isolation; reports state that local execution is not
  network isolation.
- Any aggregate, ranking or comparative product score.
