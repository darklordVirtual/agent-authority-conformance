# Agent Authority Conformance Run Protocol v0.3

**Status: draft.** Additive to [v0.2](SPECIFICATION-v0.2.md) and [v0.1](SPECIFICATION.md),
which are unchanged. This document defines how a bounded test is run against
another project's pinned artifacts, how the result is delivered privately first,
and how anyone can rerun it. The reference implementation is
[`conformance/lab/`](conformance/lab/) (`python -m conformance.lab`).

The protocol follows the principles discussed in
[aeoess/agent-governance-vocabulary#177](https://github.com/aeoess/agent-governance-vocabulary/issues/177):
independent projects, shared boundaries, verifiable evidence. The shared
principles text belongs to that common layer; this document does not restate or
own it. The delivery pattern follows the corpus-adequacy runs over REMORA
evidence-sufficiency ([REMORA-research#629](https://github.com/darklordVirtual/REMORA-research/issues/629)).

## 1. Roles

| Role | Who | Owns |
|---|---|---|
| **Producer** | The project whose artifacts are pinned (a *subject*). | Its code, fixtures, licence and roadmap. Nothing transfers to the runner. |
| **Runner** | The project executing the run. | Its verifier or adapter, fault definitions it authored, and the package. |
| **Agreement party** | Handles in `agreement_parties`. | Agreeing the scope and authorising the run. |
| **Approver** | Handles in `publication.approvers`. | Approving or declining publication, each separately. |

A run is one pilot. Taking part in one run creates no obligation to take part in
another, and verification of an artifact is not endorsement, adoption,
dependency or transfer of ownership.

## 2. Run kinds

- **verification**: the runner's own implementation reports one result per
  (input, claim): `ESTABLISHED`, `CONTRADICTED` or `NOT_ESTABLISHED`.
- **adequacy**: faults are seeded one at a time into the subject's checker;
  each is `killed` (the declared projection changed), `killed_crash`,
  `survived` or `not_measured`. It asks whether the corpus distinguishes those
  faults, not whether the checker is correct.

Both kinds run under the same lifecycle, consent log, pins, frozen plan,
package and rerun.

## 3. Independence labels

Every scope and report carries exactly one label:

| Label | Meaning |
|---|---|
| `SELF_RUN` | The runner measured its own project. Not independent evidence. |
| `SECOND_IMPLEMENTATION` | A reproduction made with knowledge of the producer's code. Not independent verification. |
| `INDEPENDENT_IMPLEMENTATION` | The runner's own implementation. Requires an `independence_statement` naming what was not imported. |

A producer-supplied report or a fresh-clone rerun of the producer's own code is
never `INDEPENDENT_IMPLEMENTATION`.

## 4. Lifecycle and gates

```
SCOPED ─freeze─▶ FROZEN ─run─▶ RUN ─package─▶ PACKAGED ─share─▶ SHARED_PRIVATE ─review─▶ REVIEWED
                                                                       │                    │
                                                                       └──── withhold ──────┼──▶ WITHHELD
                                                                                  publish ──┴──▶ PUBLISHED
```

1. **init / pin.** The scope is written in `SCOPE.json`. `pin` records the
   SHA-256 of every file under each subject's declared paths at a full 40-hex
   commit. Pins cannot change after anyone has recorded `scope_agreed`.
2. **Agreement.** Each agreement party records `scope_agreed` and
   `run_authorized` with a link to where they said so. `agreement_ref` links
   the issue where the scope was agreed.
3. **freeze.** The first call writes `RUN-PLAN-FROZEN.json` and prints its
   hash. The runner publishes the hash (a commit or issue comment) **before
   execution**; the second call records that URL and moves to `FROZEN`.
   Anchors must occur exactly once in the pinned file and Python replacements
   must parse. A changed scope, fault, control, adapter or verifier after the
   hash was printed invalidates the run.
4. **run.** Subjects are fetched again and verified byte for byte. For
   adequacy rows the unmutated baseline must match the subject's own published
   expectations when `expected_from` is declared; otherwise nothing runs.
   Pinned bytes are re-verified after every row.
5. **package.** Builds the delivery package (§6). Refused if the scope, the
   run-owned files or any result changed after `run` (their hashes are
   recorded at freeze and run), or if the package would contain a token, an
   e-mail address (outside upstream licence texts) or a local absolute path.
6. **share.** Creates `<org>/<run_id>` as a **private** repository in a GitHub
   organisation (never a user account, which cannot grant read-only access),
   verifies the package against `MANIFEST.json` and scans it again, verifies
   the repository is private before pushing, replaces any existing tree, and
   invites reviewers with read-only (`pull`) permission. Retrying after a
   partial failure is safe.
7. **review.** Factual corrections and survivor classifications, by an
   approver, agreement party or subject maintainer, are recorded in
   `CONSENT.json` and appended to `REVIEW.md`. Measured values are never
   edited.
8. **publish / withhold.** `publish` requires `publication_approved` from
   **every** approver, given after delivery (`share`) and after the latest
   factual correction, with no decline or withdrawal from any of them since
   delivery. Approvals given before anyone saw the results do not count.
   It pushes the status change as a separate commit and then makes the
   repository public. Any `publication_declined` or `withdrawn` allows
   `withhold`. A withheld or unpublished report is not citable as public
   evidence.

`CONSENT.json` is append-only and hash-chained: each event carries the SHA-256
of the canonical previous event, and `STATE.json` records the event count and
head hash after every append. Editing, deleting or truncating events is
detected and every gate refuses to proceed. Handles are GitHub handles,
compared case-insensitively without a leading `@`. This detects tampering in a
copy; it is not a signature and does not stop someone who rewrites both files.

## 5. Records

All lab JSON is canonical (sorted keys, two-space indent, UTF-8, trailing
newline). The keys `overall`, `score`, `total`, `aggregate` and `grade` are
rejected anywhere. Structures are documented in [`schema/lab/`](schema/lab/).

### 5.1 Scope

Required: `lab_version` (`"0.3"`), `run_id`, `kind`, `agreement_ref` (null
until agreed), `independence`, `runner`, `agreement_parties`, `subjects`
(project, maintainers, repo, commit, paths, files_sha256, license,
attribution), `claim_ceiling` (nonempty `establishes` and
`does_not_establish`), and `publication` (`private_first: true`,
`unreleased_citable: false`, `approvers`).

Adequacy adds `rows` (id, command containing `{case}`, projection, fault_sets,
cases, optional expected_from), `controls` (positive, inert) and `engine`
(`native` or `corpus_adequacy`, optional `cross_check` with the other one).
An adequacy run measures exactly one subject.

Subject repositories must be https URLs. Verification adds `inputs` (id,
subject index, path; a directory path is a bundle of its `.json` files keyed by
relative path) and `claims` (id, text,
layer, `check` as `<module>:<function>` in `verifier/`, `reads_fields`,
`inputs`, optional `temporal`). A temporal claim requires `reference_time`.

### 5.2 Verification results

`results/claims.json` holds one record per (input, claim) with `execution`
(`COMPLETED`, `INVALID_INPUT`, `UNSUPPORTED`, `ERROR`) and `result`:

- `COMPLETED` carries `ESTABLISHED`, `CONTRADICTED` or `NOT_ESTABLISHED`,
  the fields actually `reads` (a subset of the claim's declared
  `reads_fields`) and `unresolved_obligations` (nonempty exactly for
  `NOT_ESTABLISHED`).
- Anything else carries `result: null` and a `verifier_error`. A verifier
  crash is never a finding, and an input that cannot be read yields
  `INVALID_INPUT` for every claim on it.

When transcribed into a v0.2 assessment: `ESTABLISHED`↔`PASS`,
`CONTRADICTED`↔`FAIL`, `NOT_ESTABLISHED`↔`NOT_ESTABLISHED`, and the v0.2
evidence-tier rules still apply.

The producer's published expectations (`producer-expected.json`) are never
passed to a check. They are compared only after every record exists, and
agreement is reported in a separate table that is not a result.

### 5.3 Faults and controls

A fault set has `name`, `set` (`known` or `held_out`), `source` (author and
https reference) and faults (`id`, `class`, `file` relative to the subject,
`anchor`, `replacement`).
Controls are single faults with `polarity` `positive` or `inert`. A held-out
set becomes known once disclosed; the report says so. Faults with no pinned
input expected to distinguish them are allowed and, if they survive, are
reported as corpus discrimination limits.

### 5.4 Adequacy rows

Per mutant: `killed`, `killed_crash`, `survived` or `not_measured` (an engine
verdict the lab does not map, kept verbatim). Row status:

- `MEASURED`: the positive control was killed by a projection change and the
  inert control left every projection unchanged;
- `VOID_NO_SCORE`: the positive control was not killed (a crash does not count);
- `VOID`: the inert control changed or crashed anything.

Counts are per row and per named fault set. Nothing is summed across rows or
sets, and there is no percentage.

## 6. Package

| File | Content |
|---|---|
| `STATUS.md` | PRIVATE, PUBLISHED or WITHHELD, and whether it is citable. |
| `REPORT.md` | Independence label, pins, plan hash, claim ceiling, per-row or per-claim tables, controls, survivors, crash kills, cross-check, limits. |
| `SCOPE.json`, `CONSENT.json`, `STATE.json`, `REVIEW.md` | Scope and lifecycle records. |
| `RUN-PLAN-FROZEN.json` | Pins, run-owned file hashes, engine identity, SHA-256 of every lab module, rows; environment kept outside the hash. |
| `faults/`, `controls/`, `adapter/`, `verifier/` | Exactly what ran. |
| `results/` | Results; engine-native reports under `results/engine/`; cross-checks under `results/cross-check/`. |
| `MANIFEST.json` | SHA-256 and size of every file except the lifecycle files and `reruns/`. |
| `ORIGINAL-TO-DELIVERY.json` | Present only when an engine report was transformed for delivery, with both digests. |
| `REPRODUCE.md`, `rerun.py`, `lab/` | Rerun instructions, entry point and the vendored lab code. |
| `NOTICE`, `UPSTREAM-LICENSE-<n>.txt` | Attribution and upstream licence texts. |
| `.github/workflows/rerun.yml` | Optional manual rerun in CI. |

## 7. Rerun

`python3 rerun.py` in a package (or `python -m conformance.lab rerun <path>`):

1. verifies `MANIFEST.json` (missing, changed or unlisted files fail);
2. fetches every subject at its pinned commit and verifies every pinned hash;
3. recomputes the plan hash with the vendored code and compares it with
   `RUN-PLAN-FROZEN.json`;
4. reruns every row or claim and compares per mutant or per claim.

| Outcome | Exit |
|---|---|
| `REPRODUCED` | 0 |
| `DIVERGED` (diff written to `reruns/`) | 1 |
| `NOT_REPRODUCIBLE` | 2 |

A different Python minor version is a warning. A different subject commit is
not a rerun: `init --follow-up <run_id> --commit <sha>` starts a new run that
inherits faults and controls, links the previous plan hash, and leaves the
earlier result unchanged.

## 8. Engines

The **native** engine (standard library) copies the exported subject tree,
applies one anchor replacement, runs the row command once per case in a
subprocess with a minimal environment and a timeout, and reads the projection
from the last non-empty stdout line. The **corpus_adequacy** engine drives a
checkout of [corpus-adequacy](https://github.com/corpus-adequacy/corpus-adequacy)
pinned by commit (default `5fa2ff587497b00ac684a767335b9068f7e520a6`) and
translates its verdicts. A cross-check runs both; disagreements are engine
findings and never change the subject's row result.

## 9. Limits

Local execution is not network isolation. A schema-valid scope is well-formed,
not agreed; an agreed scope is not a result; a result is bounded by its claim
ceiling. A survivor says the corpus did not distinguish that fault on the
declared projection; it does not say the checker has it. None of this is a
certification, a ranking or a security score.
