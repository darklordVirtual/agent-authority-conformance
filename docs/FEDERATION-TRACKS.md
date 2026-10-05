# Federation tracks: self-service and manual runs

**Status:** experimental tooling in AACP. It is not a shared federation format, a
certification programme or a federation authority. It follows the principles drafted from
[aeoess/agent-governance-vocabulary#177](https://github.com/aeoess/agent-governance-vocabulary/issues/177)
and the decision rules discussed in
[#185](https://github.com/aeoess/agent-governance-vocabulary/issues/185). The offer format
below is AACP's own and optional. Anything that should become shared goes through the #185
process, and only after a second producer has used it and an implementation with no code in
common agrees on the fixtures.

A bounded verification of another project's pinned artifacts can be operated in two ways.
Both use the same pins, procedure, negative controls, result vocabulary
(`ESTABLISHED`, `CONTRADICTED`, `NOT_ESTABLISHED`; `INVALID_INPUT`, `UNSUPPORTED`, `ERROR`,
`NOT_ADMITTED` are non-verdicts), provenance fields, unresolved obligations and claim
ceilings. What differs is **when** consent is given, not **whether** it is given.

| | Self-service (S) | Manual (M) |
|---|---|---|
| Who opts in | The producer, once per frozen artifact version, in its own repository | Each agreement party, per run |
| Human gates per run | None | Scope confirmation (may be conditional), run authorisation, admission, review, publication |
| Inputs | Pre-admitted by the offer | Admitted one by one before inference |
| Kinds | Verification only | Verification and adequacy (seeded faults) |
| Producer code | Never executed | Only under an explicit scope |
| Publication | As the offer states: immediately, or after the producer's own review window | Every approver, after delivery and after the latest correction |
| Record | `self_service_run`, `published, unreviewed` unless the producer reviewed | `manual_run`, `published after review` |
| Can stand as a formal pilot result | No | Yes, if the parties agree |

An S result can later be taken through M on the same frozen pins. An M result is never
silently relabelled S. A scope without `track` is manual, so every run recorded before
tracks existed keeps its meaning.

## What tooling does and does not do

Automated: pin hashing, revision checks, offer checks, admission against the offer, schema
validation, frozen-plan hashing, execution of declared checks and controls, run capture
(arguments, working directory relative to the workspace, start and end time, exit status,
executing lab revision), the negative runner self-test, packaging with a leak scan, rerun,
and export of an evidence record.

Never automated: consent, scope confirmation, admission decisions in M, claim ownership,
publication approval, a project's node or its side of an edge, governance participation or
anything economic. Silence is never recorded as agreement.

## Producer: open an offer (S)

Commit `aacp-offers.json` in your repository. See
[the example](../templates/offers/aacp-offers.example.json) and
[the schema](../schema/lab/offers.schema.json).

- An offer covers only artifacts in the repository that commits it: `subject.repo` must be
  the repository holding `aacp-offers.json`. An offer cannot grant consent, claim ownership or
  publication rights for another project.
- `subject` pins one full commit and the paths. An offer cannot contain the commit that
  contains it, so offer a commit that already exists.
- `procedure` names the procedure that may be run (`id`, `description`, `verifier:
  "runner_owned"`). The runner brings its own checks, and producer code is never executed. A
  scope must name the same `procedure`.
- A claim may list `negative_controls`: offered inputs on which the claim must not be
  `ESTABLISHED`. The runner must keep them. They are evaluated only after every result
  exists, and checks never see them.
- `inputs` are the files you pre-admit. `claims` are the claims you open, each with its own
  `claim_ceiling`. The runner must carry that ceiling unchanged.
- `kinds` is `["verification"]` and `executes_producer_code` is `false`. Adequacy, mutation of
  your checker and execution of your code always need M.
- `publication.mode` is `PUBLIC_IMMEDIATE`, or `PUBLIC_AFTER_REVIEW` with
  `review_window_days`. `unresolved_disagreement` is `PUBLISH_WITH_DISAGREEMENT` or `HOLD`.
  Because you wrote the window into your own offer, a run published after an unanswered
  window says *no producer response within the window; not agreement*.
- Revoke by setting `revoked: true` or by removing the entry on your default branch. Revocation
  stops new freezes, runs and publications. It does not change anything already published.
- An offer is consent to bounded runs of the named claims only. It is not endorsement,
  membership, governance participation, agreement to any economic model or consent to another
  pilot.

## Public-boundary compatibility

For public artifacts, AACP can also use a pinned `public_boundary` instead of requiring the producer to publish an AACP-specific offer. This follows the self-service direction in agent-governance-vocabulary #177: a public frozen artifact, procedure, claim limits and classification rules may be operated without per-run maintainer guidance.

This path is intentionally narrower than a producer offer:

- the boundary is pinned by repository, full commit, path and SHA-256;
- the scope records where the procedure, claims and classification rules are defined;
- input admission is attributed to the **runner**, not to the producer;
- AACP publishes only the runner's attributed result;
- it does not record producer consent, review, endorsement, project approval or a statement in the producer's name;
- it never infers stronger claims from the fact that an artifact is public.

Private/unreleased artifacts and statements made in another project's name remain on the manual path. `aacp-offers.json` remains available when a producer wants to publish explicit AACP-native terms, but it is no longer a prerequisite for operating an already-public bounded reproduction target.

## Runner: self-service sequence

```sh
aacp run init <run_id> --template <scope.json>   # track: self_service, offer: {repo, commit, path, offer_id, sha256}
aacp run pin <run_id>                             # checks the scope against the pinned offer
aacp run freeze <run_id>                          # prints the plan hash; publish it, then:
aacp run freeze <run_id> --published-ref <URL>    # or --not-preregistered (reported as such)
aacp run run <run_id>
aacp run package <run_id>
aacp run share <run_id> --org <your-org>          # private first, in your organisation
aacp run publish <run_id>                         # when the offer allows it
aacp export map <run_id> --out <dir>              # evidence record; a person opens any map PR
```

`aacp next <run_id>` shows what the run is waiting for at any point.

## Runner: manual sequence

```sh
aacp run init <run_id> --template <scope.json>
aacp run pin <run_id>
# each agreement party states agreement where the scope was agreed; record what they said:
aacp run consent <run_id> --who <party> --action scope_agreed --ref <URL> [--condition "claim_a,claim_b=text"]
aacp run consent <run_id> --who <party> --action run_authorized --ref <URL>
aacp run freeze <run_id>  &&  aacp run freeze <run_id> --published-ref <URL>
aacp run admit <run_id> --input <id> --decision ADMITTED|NOT_ADMITTED|UNKNOWN --rationale <text> --who <h> --ref <URL>
aacp run run <run_id>  &&  aacp run package <run_id>  &&  aacp run share <run_id> --invite <maintainers>
aacp run review <run_id> --who <maintainer> --corrections <URL>
aacp run consent <run_id> --who <approver> --action publication_approved --ref <URL>
aacp run publish <run_id>    # or withhold after a decline
```

Admission decisions are recorded by runner maintainers, agreement parties or subject
maintainers. A manual scope may also name a `procedure` and declare per-claim
`negative_controls`, so both paths can run the same procedure.

Phase rules: `scope_agreed` and `run_authorized` only before freeze, `admission` only between
freeze and run, `review_ack` and corrections only after delivery. A post-run review is never
prior authorisation. A `withdrawn` event from any agreement party stops freeze and run, and
agreeing again means a new run. A condition must name the claims it qualifies. The report and
the export carry it under those claims.

## Records a runner should fill in

- `runner` and, when someone else wrote the verifier or adapter, `verifier_authors`.
- `runner_authored`: what the runner wrote among the inputs or procedure.
- `independence`: `SELF_RUN`, `REPRODUCTION`, `SECOND_IMPLEMENTATION` or
  `INDEPENDENT_IMPLEMENTATION` (with a statement of what was not imported). These read as
  `AUTHOR_RUN`, `REPRODUCTION`, `SECOND_IMPLEMENTATION` and `INDEPENDENT_IMPLEMENTATION` in
  federation-run-v1, and as BCR-0 to BCR-3 at most. A label alone does not establish
  independence. A claim can be marked `independent: false` with a reason, never more
  independent than its run.
- `trust_material`: keys and trust roots the checks rely on, for example *the pinned keys
  are the fixture's published test keys*.
- Per-claim `claim_ceiling` where a producer stated limits for that claim.

## Negative controls and comparison

Each declared negative control is reported as `discriminated`, `did not discriminate` or
`not exercised` (when the result was a non-verdict), in `results/controls.json` and in the
report. A control that did not discriminate means the run did not show the procedure can
fail on that input.

`aacp run compare <run_a> <run_b>` lists two verification runs of the same claims side by
side, for example a manual and a self-service run, or runs by two different tools. It shows
each run's provenance and whether the pinned inputs are identical. It never combines the
runs: there is no score, no count of matching rows and no majority. Different tools may
establish different bounded facts, and disagreement is itself evidence.

A small experiment needs only this:
1. take one frozen boundary;
2. keep its manual procedure;
3. let the producer expose the same procedure through an offer;
4. have another participant operate it without maintainer help;
5. compare the run records.

## Map export

`aacp export map` writes `evidence/<run_id>.yaml` in the shape of the systems-map prototype
(aeoess/agent-governance-vocabulary#187, pinned in `format_ref`). That prototype is not
adopted, so only the exporter changes if the format does.

The exporter:
- writes only the runner's own evidence record;
- never writes `owner_confirmation`, project files or edges on another project's behalf;
- never opens a pull request;
- refuses an unpublished run unless `--include-unpublished`, and then omits results.

Owners check the facts that concern them before any merge.

## AI assistance

Agents may run the mechanical steps and draft text for human steps. A consent event records
`drafted_by: agent:<id>` and `ai_assisted: true` when the linked statement was drafted that
way. `who` is always the person whose statement it is, and `ref` links where they made it. A
draft never counts as anyone's statement or as evidence. Public comments prepared with AI say so.

## Negative runner self-test

`aacp run selftest` builds a throw-away run whose verifier fails after every pin check. It
reports `nonzero_exit`, `no_results_written` and `no_success_line` separately. Package rerun
workflows run it before `rerun.py`. The failure mode was found by imokokok (#177, 2026-10-02)
and is recorded as Agent Errata E030. The self-test certifies no runner, and accepting a
runner remains the operator's decision.
