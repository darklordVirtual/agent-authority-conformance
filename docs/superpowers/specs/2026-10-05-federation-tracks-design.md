# Federation tracks: optional self-service and stricter manual runs — design

**Date:** 2026-10-05
**Status:** design, awaiting maintainer review
**Branch:** `feat/federation-tracks` (from `feat/v0.3-run-protocol`, merges `origin/main` at `dc7ad37`)

## 1. Purpose

Support the principles discussed in
[aeoess/agent-governance-vocabulary#177](https://github.com/aeoess/agent-governance-vocabulary/issues/177),
the decision rules in [#185](https://github.com/aeoess/agent-governance-vocabulary/issues/185) and the
record-based systems map in [#186](https://github.com/aeoess/agent-governance-vocabulary/issues/186)
with tooling that scales, by offering two optional tracks for a cross-project run:

- **Self-service (S)**: voluntary and light. A producer gives standing consent once per frozen
  artifact version; any runner may then run, publish and export without per-run human gates.
- **Manual (M)**: stricter, per run. Per-side scope confirmation (possibly conditional), run
  authorisation, input admission, private delivery, factual review and per-party publication consent.

AACP stays a tool, not an authority. It reads and writes the federation's records but does not
introduce its own formats as shared ones. The new offer format is AACP's own and optional; it is
proposed through the #185 process only after a second producer has used it.

### Decisions already taken (2026-10-05)

| Question | Decision |
|---|---|
| First contribution | Tooling first: AACP enforces the run contract and exports map records |
| Where runs execute | Local by default; optional private CI in the runner's organisation; public CI only under a public offer |
| AI in human gates | Agents may complete mechanical steps and draft judgement steps, labelled `drafted_by: agent:<id>`; only a named person's statement, linked by URL, counts |
| Track model | Both tracks, chosen per run; S results can be promoted to M, never silently downgraded |

### Success criteria

1. A third party can run a bounded verification against a producer's offer with no involvement from
   us or the producer, and the result is labelled `self_service`, `unreviewed`.
2. A manual run cannot execute without each side's scope confirmation and run authorisation, cannot
   run an input that was not admitted, and cannot publish without every approver's consent after delivery.
3. Conditions attached to a scope confirmation are carried with the claims they qualify into the report and export.
4. Either track exports an evidence record in the shape of the #187 prototype without inventing owner
   confirmation, and without disclosing results of an unpublished run.
5. Existing v0.3 scopes, packages and the REMORA v1.2 reference run remain valid (no `track` means M).

## 2. Invariants (both tracks; never relaxed)

- Full 40-hex commit pins and raw-byte SHA-256 for every pinned file.
- One result per (input, claim) with execution status; non-verdicts stay non-verdicts.
- Claim ceilings per claim; no aggregate keys (`overall`, `score`, `total`, `aggregate`, `grade`).
- The runner and what the runner authored are recorded; independence is per claim.
- Run contract: fresh run directory, contemporaneous capture of argv, start/end time and exit status,
  and an E030-style negative runner self-test that reports its three assertions separately.
- Silence is never agreement. Nothing is retroactive. Earlier results are never edited.

## 3. Track S: open verification offer

### 3.1 Offer file (producer-owned)

The producer commits `aacp-offers.json` in its own repository (path chosen by the producer):

```json
{
  "schema_version": "aacp-offers-v1",
  "offers": [{
    "offer_id": "agentavow-tmd-v1",
    "revoked": false,
    "expires": "2027-04-01",
    "producer": {"project": "AgentAvow", "maintainers": ["kenneives"]},
    "subject": {"repo": "https://github.com/AgentAvow/AgentAvow", "commit": "<40-hex>", "paths": ["docs/standards/tool-manifest-digest-vectors-v1"]},
    "inputs": [{"id": "vectors", "path": "docs/standards/tool-manifest-digest-vectors-v1/vectors.json"}],
    "claims": [{"id": "tool_digest_binds", "text": "...",
                "claim_ceiling": {"establishes": ["..."], "does_not_establish": ["..."]}}],
    "kinds": ["verification"],
    "executes_producer_code": false,
    "publication": {"mode": "PUBLIC_IMMEDIATE", "review_window_days": null,
                    "unresolved_disagreement": "PUBLISH_WITH_DISAGREEMENT"}
  }]
}
```

Rules (validated by the lab, standard library only):

- `executes_producer_code` is the constant `false`; `kinds` may contain only `verification`.
  Adequacy, mutation of a producer checker or execution of producer code always need track M.
- `publication.mode` is `PUBLIC_IMMEDIATE` or `PUBLIC_AFTER_REVIEW`; the latter requires
  `review_window_days` ≥ 1. `unresolved_disagreement` is `PUBLISH_WITH_DISAGREEMENT` or `HOLD`.
  Because the producer wrote the window into its own offer, publishing after an unanswered window
  does not treat silence as agreement: the record says *no producer response within the window; not endorsed*.
- `inputs` is the producer's pre-admission: listed inputs are admitted by the offer.
- Revocation: the producer sets `revoked: true` (or removes the entry) on its default branch.
  A newer offer is added as a new entry; it does not revoke older ones.

### 3.2 Scope for an S run

`SCOPE.json` gains `"track": "self_service"` and
`"offer": {"repo", "commit", "path", "offer_id", "sha256"}` (the offer file's raw-byte hash at that commit).
For S, `agreement_parties`, `agreement_ref` and `publication.approvers` are not required; `runner` is.
At `pin` the lab fetches the offer at its commit and checks:

- the file hash, schema and `offer_id`;
- the scope's single subject equals the offer subject (repo, commit, paths);
- scope inputs ⊆ offer inputs and scope claim ids ⊆ offer claim ids;
- each scope claim carries the offer's ceiling for that claim (copied, not edited);
- `kind` is in `offer.kinds`.

At `freeze`, `run` and `publish` the lab re-reads the offer at the repository's default-branch tip and
refuses if the entry is missing or revoked, or if `expires` has passed. A result already published stays published.

### 3.3 S lifecycle

```
SCOPED ─freeze─▶ FROZEN ─run─▶ RUN ─package─▶ PACKAGED ─share─▶ SHARED_PRIVATE ─publish─▶ PUBLISHED
                                                                      │  (review optional)
                                                                      └─withhold─▶ WITHHELD (HOLD + producer decline)
```

- `freeze` needs no consent. `--published-ref` is optional; without it the report states
  `preregistered: false`.
- `publish` is allowed from `SHARED_PRIVATE` (or `REVIEWED`) when the offer is valid and:
  `PUBLIC_IMMEDIATE`, or `PUBLIC_AFTER_REVIEW` with `review_window_days` elapsed since `share`.
  A producer `publication_declined` during the window with `HOLD` blocks publishing and allows `withhold`;
  with `PUBLISH_WITH_DISAGREEMENT` the decline is published with the record.
- Factual corrections by a producer maintainer during the window use the existing `review` command.
- In S, "producer" for declines and corrections means `offer.producer.maintainers`; no other handle's
  decline affects publication, and no approval is ever required.

## 4. Track M additions

The existing v0.3 lifecycle and gates stay. Additions:

1. **Conditional scope confirmation.** A `scope_agreed` event may carry
   `conditions: [{"text": "...", "claims": ["<claim id>", ...]}]`. `package` refuses a condition
   that names no claim or an unknown claim. The report and export render each condition under the
   ceiling of every claim it names.
2. **Admission.** New consent action `admission` with `input`, `decision`
   (`ADMITTED`, `NOT_ADMITTED`, `UNKNOWN`) and `rationale`. Allowed after every party's
   `run_authorized` and before `run`. `run` refuses unless every input has an admission event;
   claims over an input whose latest decision is not `ADMITTED` get
   `execution: "NOT_ADMITTED"`, `result: null`, `verifier_error.code: "not_admitted"`.
   The admission events' consent indices are recorded with the results.
3. **Review acknowledgement.** New action `review_ack`: a maintainer reviewed the package as
   clarification only; it is not approval of results or release and does not satisfy any gate.

## 5. Event provenance (both tracks)

Every consent event gains optional `drafted_by` (`"human"`, default, or `"agent:<id>"`) and
`ai_assisted` (bool, default false). `who` is the person whose statement it is and `ref` links that
statement; the fields disclose how the text at `ref` was produced. They do not change gate logic.
`recorded_by` records the handle that operated the tool when it differs from `who`.

## 6. Independence and authorship per claim

- Scope `independence` gains `REPRODUCTION` (runner reran the producer's own verifier; BCR-1).
- Scope gains `runner_authored` (list of strings, may be empty).
- Each claim may carry `independent: false` with `not_independent_reason`. Default: independent only
  when the run label is `INDEPENDENT_IMPLEMENTATION` and no input the claim reads is runner-authored.
- Mapping used by the report and export:

| Lab label | federation-run-v1 | BCR |
|---|---|---|
| `SELF_RUN` | `AUTHOR_RUN` | BCR-0 |
| `REPRODUCTION` | `REPRODUCTION` | BCR-1 |
| `SECOND_IMPLEMENTATION` | `SECOND_IMPLEMENTATION` | BCR-2 |
| `INDEPENDENT_IMPLEMENTATION` | `INDEPENDENT_IMPLEMENTATION` | at most BCR-3 (BCR-4 needs separate host evidence) |

## 7. Run contract

- `run` writes `results/run-capture.json`: argv with paths made relative to the run directory,
  `started_at`, `ended_at`, `exit_status`, Python version and platform. Absolute paths never enter the
  package (the leak scan still applies). The capture is listed in `MANIFEST.json` but outside the plan hash.
- `aacp run selftest` creates a throw-away run whose verifier raises after setup and reports three
  separate fields: `nonzero_exit`, `no_results_written`, `no_success_line`. Any field false is a failure.
  The test suite and the package's rerun workflow invoke it.

## 8. CLI

`aacp` becomes the single entry point; `python -m conformance.lab` keeps working.

| Command | Does |
|---|---|
| `aacp run <lab subcommand> ...` | Passes through to the lab (init, pin, consent, admit, freeze, run, package, share, review, publish, withhold, status, rerun, selftest) |
| `aacp run admit <run> --input --decision --rationale --who --ref` | Records an admission event (M) |
| `aacp run consent ... --condition "<claim>[,<claim>]=<text>" --drafted-by --ai-assisted` | Extended consent |
| `aacp next <run> [--json]` | State, track, outstanding mechanical checks and human actions (who, what, why), next command. Never proposes an event on another person's behalf. Uses the `aacp-command-result-v1` envelope with `verification_status: NOT_RUN` |
| `aacp export map <run> --out <dir> [--include-unpublished]` | Writes `evidence/<run_id>.yaml` in the #187 shape |

Packaging: `pyproject.toml` adds `conformance`, `conformance.lab` and its subpackages.
`load_config` reads `lab.toml` from the current directory first, then the repository root, so an
installed `aacp` works in any project.

## 9. Map export

Target: the evidence-record fields of the #187 prototype, recorded in the output as
`format_ref` with the PR head commit, so a later change to the shared format replaces only the exporter.

| #187 field | Source |
|---|---|
| `id` | `run_id` |
| `type` | `self_service_run` or `manual_run` |
| `source` | package repository and delivery commit (or `local`) |
| `record_state` | `published, unreviewed` (S) · `published after review` · `private, not published` |
| `runner`, `runner_authored` | scope |
| `independent_for`, `not_independent_for` | per-claim independence (§6) |
| `results_as_emitted` | counts per result category, only when published |
| `reviews` | `review` and `review_ack` events |
| `note` | track, ceiling conditions, `preregistered`, AI-assistance disclosure |

The exporter never writes `owner_confirmation` or project files, and never opens a PR. For a run that is
not `PUBLISHED` it refuses unless `--include-unpublished`, in which case results are omitted and
`record_state` is `private, not published`.

## 10. Private CI

The package's existing `.github/workflows/rerun.yml` stays `workflow_dispatch` only with
`contents: read`, runs `selftest` and then `rerun`, uploads nothing, and is the template for running in
a private repository of the runner's organisation. Public CI is used only for S runs whose offer is
`PUBLIC_IMMEDIATE`. A reusable published Action is out of scope.

## 11. Integration with main

Merge `origin/main` (PRs #5–#11: adapters, federation schemas, AGENTS.md, `aacp` CLI) into the branch.
Text conflicts in `.gitignore`, `CHANGELOG.md` and `README.md` are resolved by keeping both. The lab keeps
its two-space canonical JSON profile, which is documented as distinct from the adapter's compact profile.

## 12. Out of scope

Profile registry, `consumer-contract-v1`, `verifier-manifest-v1`, `bcr-run-v1` schema, `aacp resolve`,
reusable GitHub Action, PyPI publication, attribution receipts and any change to another project's records.

## 13. Testing

Standard-library `unittest`, local file-URL git repositories as in the existing lab tests, no network.

- Offer: valid, hash mismatch, unknown claim/input, subject mismatch, adequacy kind, revoked at tip,
  removed at tip, expired, `PUBLIC_AFTER_REVIEW` before and after the window, decline with `HOLD` and
  with `PUBLISH_WITH_DISAGREEMENT`.
- M: condition with unknown claim refused at package; condition rendered per claim; run refused without
  admission; `NOT_ADMITTED`/`UNKNOWN` produce non-verdicts; `review_ack` satisfies no gate.
- Provenance fields stored and hash-chained; old events without them still verify.
- Independence: per-claim derivation and mapping table.
- Run capture has no absolute path; selftest's three fields; selftest detects a wrapper that swallows failure.
- `aacp next` envelope validates; never lists another person's event as an action for the operator.
- Export: S published, M published, M unpublished refused, `--include-unpublished` omits results, no `owner_confirmation`.
- Backward compatibility: existing fixtures, templates and `runs/remora-es-v12-adequacy` validate unchanged.
- Full existing suites on the merged branch (`python -m unittest discover -s tests`, conformance checks).
