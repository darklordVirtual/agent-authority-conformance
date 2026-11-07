# ADR-0002: Frozen integer revisions; profile results as `bcr-run-v1` records

**Status:** PROPOSED (awaiting maintainer decision; the record format is the decision that most affects Stage 1)
**Addresses:** adversarial review B-02, S-01, S-02; proposal §0 decision 3, §2, §2.2; AC-02

## Context

1. **Versioning.** TERMINOLOGY.md and GOVERNANCE.md: a profile revision is an integer and is
   frozen when merged; later fixtures go into a new revision. The proposal's example uses
   `profile_version: "1.0.0-draft"`.
2. **Record format.** METHOD.md already commits AACP to one new record type, the planned
   `bcr-run-v1`, "with `schema/federation-run-v1.schema.json` as its starting point". It
   lists a result vocabulary: `ESTABLISHED`, `CONTRADICTED`, `NOT_ESTABLISHED`,
   `NOT_APPLICABLE`, `INCOMPATIBLE`, `NOT_RUN`. The proposal introduces a second new type,
   `aacp-profile-assessment-v0.1`, with execution, conclusion and v0.2-style assessment
   fields.
3. **Layout.** GOVERNANCE.md asks for `profiles/<name>/v<n>/` with the six profile parts
   and a `CLAIM_CEILING.md`. The proposal suggests single files under `profiles/` and
   vectors under `vectors/profiles/`. The two existing profiles already use single files,
   which is a separate, pre-existing discrepancy.

## Decision (proposed)

1. **Revisions** are integers frozen on merge. "Draft" is the status of an unmerged
   proposal, expressed in the profile's status line, never in its revision string. No record
   may cite an unmerged profile.
2. **Record format.** Recommended: profile results are `bcr-run-v1` records, one record type
   for every AACP profile, old and new. Stage 1 then specifies `bcr-run-v1` (from
   `federation-run-v1`) rather than a parallel envelope. If the maintainer chooses the
   proposal's separate envelope instead, Stage 1 must include an explicit, tested mapping
   from that envelope to `bcr-run-v1` fields, so AACP does not maintain two unrelated
   result systems.
3. **Vocabulary.** The METHOD.md result vocabulary is the conclusion vocabulary. The lab's
   execution statuses (`COMPLETED`, `UNSUPPORTED`, `INVALID_INPUT`, `ERROR`, `NOT_ADMITTED`)
   are kept as execution states. A v0.2 `PASS`/`FAIL` appears only through the existing
   transcription rule (RUN-PROTOCOL-v0.3 §5.2), never as a native field. Allowed
   combinations are fixed in ADR-0003.
4. **Layout.** New profiles follow GOVERNANCE.md: `profiles/<name>/v1/` containing the
   normative claim, input contract, positive fixtures, negative and mutation fixtures,
   procedure and `CLAIM_CEILING.md`, with a `SHA256SUMS` over the fixtures. The existing
   single-file profiles are left as they are; aligning them is out of scope here.

## Consequences

- One result type for all profiles keeps comparison, rerun and export (map) code single.
- `bcr-run-v1` must be specified before any H, I or J record exists. That is Stage 1 work
  and moves part of METHOD.md from "planned" to specified, which needs its own review.
- The proposal's `independence.bcr_level` becomes the record's `level`, cross-checked
  against declared roles (ADR-0003).

## Alternatives considered

- **Separate `aacp-profile-assessment-v0.1`** (as proposed): workable, but duplicates the
  planned record type and adds a third vocabulary. Acceptable only with the mapping above.
- **Extend the v0.2 assessment schema:** rejected, it would reinterpret frozen records
  (proposal decision 1, AC-01).
