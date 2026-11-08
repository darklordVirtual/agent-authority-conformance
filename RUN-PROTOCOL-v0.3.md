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

An input may set `format` to `json` (the default, as above) or `bytes`. A
`bytes` file reaches the check as `{name: bytes}`; a `bytes` directory as
`{relative path: bytes}` of every file under it. Use `bytes` whenever a check
verifies a signature or a digest: re-serialised JSON is not the signed message.
A file's evidence digest is its SHA-256; a bundle's is the SHA-256 of the
canonical `{path: sha256}` map.

A verification scope may add `probes` (§5.5) and, for any run, `challenge`:
`ref` (https link to a public request to verify something), `by`, `asked` (what
it asked, in the runner's words) and `requests_endorsement`. A challenge is
context only. It is never consent, an offer, admission or a publication
approval, it satisfies no gate, and answering it is not endorsement; the report
says so, and says explicitly that no endorsement is given when one was asked for.

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

### 5.5 Probes

A probe records a property the runner observed about the pinned bytes: a
specification that the published code does not follow, a construction that
admits two inputs with one digest, a field a signature does not bind, an
unannounced key change. Probes are separate from claims because they are the
runner's own questions, often formed after reading the subject, and they must
never borrow the standing of a claim result.

A probe declares `id` (unique among claims and probes), `text` (the property
probed, stated neutrally), `class` (`SPEC_IMPLEMENTATION_DIVERGENCE`,
`CONSTRUCTION_AMBIGUITY`, `BINDING_GAP`, `FRAMING_GAP`, `KEY_REUSE`,
`TRUST_ANCHOR`, `ATTESTATION_SCOPE`, `TERMINOLOGY_CHANGE`, `PROVENANCE_ATTRIBUTION` or
`OTHER`),
`check`, `inputs`, `reads_fields`, `runner_assessment` (`level`
`informational`, `low`, `medium` or `high`, with a `rationale`) and optionally
`remediation` and `source_locators` (subject, pinned path, line range, note;
after `pin` the path must be a pinned file). Locators point at bytes that were
read; they are never executed.

Unlike a claim, a probe runs once over all its inputs together, so it can
compare two pinned revisions. The check receives `{input id: document}` and
returns `observation` (`DEMONSTRATED` or `NOT_DEMONSTRATED`), `reads`,
`witness` (plain JSON, no floats, no aggregate keys, nonempty when
`DEMONSTRATED`), `affects_pinned_artifact` (true when the observation holds
for the bytes as published, false when shown only on constructed inputs) and
`message`. Contract violations and crashes are `ERROR` non-verdicts; an input
that is not admitted or cannot be read makes the probe `NOT_ADMITTED` or
`INVALID_INPUT` without running it. Records go to `results/probes.json`
([schema](schema/lab/probe-results.schema.json)), are compared on rerun
including the witness, and are reported in their own section. A probe never
maps to `PASS` or `FAIL`, assessment levels are never summed, and the report
does not count probes.

A public-boundary run (§9) is bound to its boundary: every subject must be a
revision of the boundary's own repository, with one subject as with several,
and subject 0, the primary subject, must be pinned at the boundary commit, so
the boundary text describes exactly the bytes verified. Further subjects are
other revisions kept for comparison. The basis never covers a second project.

Probes describe what the pinned bytes show. A difference between two revisions
supports a statement about the difference (for example that an identifier
changed meaning), not about where code or a construction came from; that needs
its own evidence and is outside every probe in this protocol.

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

`respond <run_id>` drafts a public reply to a challenge from the run's own
records: pins and every pinned file digest, the frozen plan hash and whether it
was preregistered, the runner's check hashes, every claim result with its
input digest, every probe with its witness and locators, the claim ceiling,
the endorsement statement and reproduce steps. It requires a measured run whose
scope, run-owned files and results are unchanged, writes outside the package
(`.local/CHALLENGE-RESPONSE.md` by default) so MANIFEST.json is untouched, and
ends with who drafted it (`--drafted-by human|agent:<id>`, `--ai-assisted`).
Inside the run directory it writes only under `.local/` (symlinks resolved), and
it replaces an existing draft only with `--force`. Findings are grouped by
`affects_pinned_artifact`: those that hold for the bytes as published come
first, and those shown only on constructed inputs say that no attack on the
published package is demonstrated. On rerun, every field of every probe record
is compared, including its message, class, inputs and any verifier error.
It states the lab status; before `PUBLISHED` the package is not citable as
published evidence, although every value in the draft is recomputable from the
pinned bytes. See [docs/CHALLENGE-RESPONSE.md](docs/CHALLENGE-RESPONSE.md).

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

## 9. Tracks

A scope may set `track` to `manual` (the default when absent) or `self_service`.
See [docs/FEDERATION-TRACKS.md](docs/FEDERATION-TRACKS.md). In brief:

- **self_service** pins a producer-owned open verification offer
  (`offer: {repo, commit, path, offer_id, sha256}`, [schema](schema/lab/offers.schema.json)).
  `pin` checks the scope against it and writes `offer_terms`. `freeze`, `run`
  and `publish` re-read the producer's default branch and refuse a withdrawn,
  revoked or expired offer. No consent event is required. Inputs are admitted
  by the offer. `freeze --not-preregistered` is allowed and reported.
  Publication follows the offer's mode and review window. A producer decline
  blocks under `HOLD` and is published with the record under
  `PUBLISH_WITH_DISAGREEMENT`. Verification only. Producer code never runs.
- **manual** adds to §4: conditional `scope_agreed` (`conditions` naming
  claims, carried into the report), `admission` per input between freeze and
  run (anything but `ADMITTED` makes that input's claims `NOT_ADMITTED`
  non-verdicts), `review_ack` (clarification only, no gate), phase rules for
  every pre-run and post-run event, and a stop on any party's `withdrawn`.
- Both: optional `drafted_by` / `ai_assisted` / `recorded_by` on every event,
  per-claim independence and `runner_authored`, `REPRODUCTION` label,
  `verifier_authors`, `trust_material`, `RUN-CAPTURE.json` for every run
  attempt, and `selftest`.

## 10. Limits

Local execution is not network isolation. A schema-valid scope is well-formed,
not agreed; an agreed scope is not a result; a result is bounded by its claim
ceiling. A survivor says the corpus did not distinguish that fault on the
declared projection; it does not say the checker has it. None of this is a
certification, a ranking or a security score.
