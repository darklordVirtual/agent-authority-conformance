# Self-service interoperability

An AI agent can start from [AGENTS.md](../AGENTS.md). A useful request is:

> Read AGENTS.md. Act as a read-only consumer for the committed REMORA adapter.
> Resolve its pinned public artifacts, produce a hash-bound run package, test
> missing and modified input, and report claim limits and next obligations.
> Do not run producer code or publish results awaiting review.

The default exercise is **resolution only**. It is immediately runnable but is
not an independent REMORA verification or a live runtime assessment.

## Resolution quick start

From this repository root, with Python 3.12+, Git and network access:

```sh
python -m pip install -r requirements-dev.txt
git clone --no-checkout https://github.com/darklordVirtual/REMORA-research.git ../remora-subject
git -C ../remora-subject checkout --detach 31c4060630923344d43d9fac26821150262c3687
python -m scripts.run_federation_adapter \
  --manifest adapters/remora-evidence-sufficiency-v1/adapter.json \
  --subject-root ../remora-subject \
  --record-dir ../remora-resolution-run-001 \
  --runner YOUR_ACTUAL_OPERATOR_ID \
  --fixture-author REMORA-research \
  --classification AUTHOR_RUN \
  --summary ../remora-resolution-summary.md
(cd ../remora-resolution-run-001 && sha256sum --check SHA256SUMS)
```

Use a new checkout/output path if these already exist. Replace the operator
placeholder with a real identity. `AUTHOR_RUN` is conservative; choose
`REPRODUCTION` only with declared external operator provenance, never because
the computer is running GitHub Actions. Fixture authorship above identifies the
producer-authored committed fixtures, not the operator.

Exit 0 means all required artifact bytes resolved; exit 1 means incomplete
resolution, not a property violation. Invalid manifests, mismatched checkout
HEAD and filesystem errors also stop the command without a property verdict.
Optional artifacts can remain unresolved without failing required resolution;
inspect each evidence row. The lightweight `--out bundle.json` mode remains
available but does not check checkout HEAD or produce run provenance.

## Choose a role

| Role | Owns | Required deliverable | Does not establish |
|---|---|---|---|
| Producer | Native contract, artifacts, fixtures and scope | Versioned package manifest, digests, claim ceiling, non-claims, verifier request and frozen pin | External verification by author run |
| Consumer | Foreign bytes and their applicability to a local use | Resolution bundle, source classes, admission obligations and explicit native-claim mapping | Authority or admission merely from resolution |
| Verifier | A bounded independently described procedure | Per-claim/per-case results, negative tests, scope, implementer/operator identities, evidence and unresolved obligations | Independence merely from a second implementation |
| Reproduction operator | Re-running a frozen procedure | Actual command, environment, procedure/input pins and comparison against committed expectations | A new independent implementation |

### Producer

1. Name one native claim and a versioned consumer contract; state assumptions,
   trust roots, process/deployment scope and real versus simulated effects.
2. Publish a package using
   [federation-producer-package-v1.schema.json](../schema/federation-producer-package-v1.schema.json)
   where appropriate. REMORA's native package format is different: preserve it
   rather than relabeling it as the AACP schema.
3. Pin every file's raw-byte SHA-256. Keep inputs, authored expectations and
   reference code separate. Include positive, missing, tampered, wrong-subject,
   stale/replayed and insufficient-evidence cases where the contract applies.
4. Commit package bytes before recording the full revision carrying them. A
   package cannot contain the Git commit that hashes that same package.
5. Propose a review/publication policy. Author tests do not advance external
   verification state; retain contradictory results and earlier package versions.

### Consumer

1. Start from a public verification request, maintainer artifact or permission.
2. Clone at the manifest's full subject revision and resolve declared hashes.
   Do not import producer runtime or reference-verifier code into consumer tests.
3. Check relevance, provenance, scope, source trust and completeness separately
   before admitting evidence. List each missing obligation and next evidence.
4. Preserve native claim IDs and result vocabulary. Use `no_mapping` or
   `not_evaluated` when an A-G inference is not supported; mapping is not credit.
5. Store a fresh run package and compare it against expectations without changing
   those expectations. Follow the frozen review gate.

### Verifier

1. Freeze the claim, input contract, hypothesis, discriminating negative cases
   and expected-result oracle before implementing a procedure.
2. Record producer, fixture author, verifier maintainer, operator and host
   control separately. State blinding and producer-code imports honestly.
3. Implement in the verifier-owned codebase. A reference checker rerun belongs
   to reproduction, not independent verification. Inspect the native schema's
   independence requirements instead of translating labels mechanically.
4. Test schema/shape, missing provenance, changed bytes, wrong scope, stale and
   replayed input, expected-answer leakage, inconclusive evidence and errors.
   For semantic changes, add a seeded fault or metamorphic discriminator.
5. Emit one result per native claim/case, with direct evidence, ceiling and
   non-claims. `INVALID_INPUT`, `UNSUPPORTED` and `ERROR` remain non-verdicts.
6. Validate against the chosen run/result schema and request factual review.
   Preserve disagreement; publish only under the frozen policy. The resolver
   command here does not implement this property-inference stage.

## Run package and hashes

`--record-dir` creates a new directory; it refuses an existing one:

| File | Meaning |
|---|---|
| `adapter.json` | Normalized copy of the consumed manifest |
| `bundle.json` | Resolution rows, null property verdicts and publication state |
| `run.json` | Existing `federation-run-v1` format, actual procedure revision, roles, command, environment and output digest |
| `SHA256SUMS` | Raw-byte SHA-256 of the three JSON files, sorted by filename |

Normalized JSON uses this repository's profile: UTF-8, sorted keys, compact
separators, unescaped Unicode and a trailing LF. It is **not RFC 8785 JCS**.
The manifest digest refers to this normalized copy; the environment separately
records the original manifest's raw-byte digest. Artifact digests always refer
to raw bytes. AACP and REMORA package digests are distinct formats.

The run ID is SHA-256 of the normalized run record **without `run_id`**. The
record names the bundle digest, never its own digest. `SHA256SUMS` hashes the
completed record and does not hash itself. Its digest appears in the summary.
Check both downloaded bytes and the checksum-file commitment from a trusted
channel; a replaceable checksum file alone does not authenticate anything.

`pins.adapter_revision` and `pins.procedure_revision` name the actually executed
AACP checkout, not the historical adapter pin declared by the input manifest.
The latter remains in the bundle and `environment.declared_adapter_revision`.
Procedure-file digests expose local changes; dirty tracked code is marked and
cannot release result details through the summary. Treat such runs as local
drafts. Commit reviewed changes before a publishable run. To reproduce a
historical resolver, separately check out its declared revision; do not pretend
the current command executed that implementation.

## GitHub Actions

Use **Actions -> Federation self-service -> Run workflow**, select a committed
adapter and declare fixture authorship and classification. The workflow checks
the manifest schema, checks out the exact public subject commit, never executes
subject code and uses the same CLI as local runs. It requires no producer token
and has read-only repository permissions. Add a new reviewed adapter through a
PR and then add its path to the workflow's fixed choices; dispatch cannot supply
an arbitrary shell command or remote manifest.

The job summary lists per-artifact resolution only for `PUBLIC_IMMEDIATE` and
a clean consumer checkout. Otherwise it lists technical commitments and states
that details are withheld. Full artifacts are uploaded only for that same gate,
with 14-day retention. Required-resolution failures still retain a public
`INVALID_INPUT` bundle when that gate permits it. Every run disclaims property
credit. Action logs/metadata and exit status are observable: use a private local
run, not public CI, if even attempting resolution is confidential.

`PUBLIC_AFTER_REVIEW`, `PRIVATE_UNTIL_APPROVED` and `PUBLIC_BY_MUTUAL_CONSENT`
do not release merely because time passes, a job succeeds or a checkbox is set.
Keep review-required bundles locally; retain the review/consent record with the
run and publish through a separately authorized reviewed contribution. Do not
change a frozen manifest to bypass the gate. GitHub artifact digests identify
the uploaded archive; `SHA256SUMS` identifies the files inside. Neither is a
signature, timestamp authority, certification or proof of independence.

## REMORA-specific next step

The existing adapter consumes the historical evidence-sufficiency corpus, not
REMORA's newer boundary packages. See [the source inspection](REMORA-INTEROP-REVIEW.md).
For a new boundary exercise, begin with REMORA's `artifacts/interop/index.json`,
select a frozen contract, verify its `freeze_record`, manifest, claim packet,
verifier request and package digest, then create a **new** adapter here. Do not
silently repin the historical corpus exercise or run the producer's scripts.