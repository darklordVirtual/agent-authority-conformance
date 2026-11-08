# Changelog

## Unreleased

- Add an assessment of Neutral Trust Infrastructure at `de08dbd`, [examples/nti-de08dbd.json](examples/nti-de08dbd.json), with its inspection record [docs/NTI-SOURCE-INSPECTION.md](docs/NTI-SOURCE-INSPECTION.md). A, B, C and D are `FAIL` on executed evidence; E, F and G are `UNTESTED`. Each `FAIL` rests on a test that passes on the pinned revision and fails when that one weakness is repaired; `scripts/run_nti_inspection.py` runs both halves from `mutations.json` and `expected.json` and writes a result record, and `.github/workflows/nti-inspection.yml` reproduces it in CI with two negative harness self-tests. The tests and mutations are the assessor's, so the runs are an author run and a reproduction, not independent. The PR #63 witness-provenance observations are recorded without an A-G mapping.

- Add `AACP-OBSERVED-EFFECT-VANTAGE-2`, a revision of the observation-vantage profile. Positive observer-independence credit now also needs runner-owned evidence that the observer identity is established outside the producer, which cannot issue or revoke it, and that the producer cannot reach the observer's signing key. `evaluate_observation_vantage_r2` and `--profile-revision 2` apply it. Revision 1 and its function stay as published, as GOVERNANCE.md requires of a merged profile revision, so the reference vectors v1 and every record under revision 1 are unchanged.

- Add frozen reference vectors, `vectors/aacp-reference-vectors-v1/`: 86 input and expected-answer pairs for nine deterministic operations (the E rule, the OE-08 observation vantage, AgentAvow tool keys, digests and bindings, the lab's canonical JSON, strict JSON reading, the no-aggregate key rule, and the A-G coverage matrix). Every expected answer names its source, a committed fixture, a producer's own published or signed expectation, or specification text written out by hand, and the build script imports none of the rules it checks. The bytes are pinned by `SHA256SUMS`, `MANIFEST.json` and a test, `scripts/build_reference_vectors.py --check` rebuilds them from their sources, and `--write` refuses to replace a frozen suite. `python -m conformance.vectors run --impl "<command>"` checks any implementation over a one-request stdio protocol and reports per vector, with no score. `tests/test_vectors_adequacy.py` seeds 34 plausible implementer faults, and every one is noticed; the first version let an implementation that never sorts keys pass, which the canonical-JSON vectors now catch by taking JSON text as input. The suite documents that the lab's canonical form is not RFC 8785 and that a repeated assessment component is a schema error. See [docs/REFERENCE-VECTORS.md](docs/REFERENCE-VECTORS.md).

- Add `AACP-OBSERVED-EFFECT-VANTAGE-1`, a neutral bounded profile derived from the pinned public RFC189 OE-08 candidate. Self-vantage cannot establish independent observation; verifier-owned trust material stays outside producer input. Includes positive/adversarial controls and a public byte-resolution adapter without granting A-G, RFC-189 or CoSAI credit.

- Add optional federation tracks ([docs/FEDERATION-TRACKS.md](docs/FEDERATION-TRACKS.md)):
  self-service runs under a producer-owned open verification offer
  (`schema/lab/offers.schema.json`), and stricter manual runs with conditional scope
  confirmation, per-input admission before inference (`NOT_ADMITTED` non-verdicts),
  `review_ack`, phase rules and withdrawal stops. Both: AI-drafting disclosure on consent
  events, per-claim independence, `REPRODUCTION` label, verifier authors, trust-material
  disclosure, run capture of every attempt and a negative runner self-test. Scopes
  without `track` are manual and unchanged.
- `aacp run`, `aacp next` and `aacp export map` (evidence records in the shape of the
  #187 systems-map prototype). The lab is packaged with `aacp`; `lab.toml` is read from
  the current directory first.

- Rename the project to Agent Authority Conformance Profiles (AACP). The
  former name is held by the LF Decentralized Trust Agent Authority
  Conformance lab. Added `CHARTER.md` (seven principles, implementation
  neutrality as a normative rule), `METHOD.md` (Bounded Claim Reproduction,
  levels BCR-0 to BCR-4, six-valued result vocabulary for the planned
  `bcr-run-v1`), `TERMINOLOGY.md` and `GOVERNANCE.md`. Schema `$id`s and
  prose now carry the new name; the v0.1 and v0.2 specifications, the
  committed assessments, the adapter manifests and the mutation definitions
  keep their text so pinned bytes and historical records are unchanged.
  `SPECIFICATION.md` and `schema/assessment.schema.json` are byte-pinned by
  `tests/test_conformance.py` and keep the former name verbatim, including
  the v0.1 `$id`.
- Add seeded-fault adequacy for the bounded E rule: `conformance/mutations-v0.2.json`
  defines 30 faults and two controls, `python -m conformance.mutations` scores the
  committed fixtures against them in memory, and seven fixtures were added so that
  no fault survives (one per missing minimum class, an extra attempted class, and
  every obligation open at once).
- Add `python -m conformance.invariants`: twelve metamorphic relations and a
  table-driven reference model checked against `evaluate` over an exhaustively
  generated space of accepted-evidence documents.
- Document both in `MUTATIONS-AND-INVARIANTS.md`; both run in CI.

## Run protocol lab 0.3 — draft, 2026-09-30

- Add the run protocol ([RUN-PROTOCOL-v0.3.md](RUN-PROTOCOL-v0.3.md)) for
  bounded, private-first runs against other projects' pinned artifacts,
  following the principles discussed in aeoess/agent-governance-vocabulary#177.
- Add `conformance/lab/` (`python -m conformance.lab`), standard library only:
  scope and fault validation, hash-chained consent log, lifecycle gates,
  two-step plan freeze, verification (per-claim) and adequacy (seeded-fault)
  run kinds, native and corpus-adequacy engines with cross-check, delivery
  package with leak scan, private GitHub share with read-only invitations,
  gated publication, and a self-contained `rerun.py`.
- Add `schema/lab/` JSON Schemas, toy fixtures and tests; external scope
  templates under `templates/scopes/`.
- v0.1 and v0.2 specifications, schemas and code are unchanged.

## 0.2 — draft, 2026-09-15

- Add versioned evidence-sufficiency semantics: completed `NOT_ESTABLISHED`
  is distinct from untested properties and verifier failures.
- Require nonempty, pinned resolved evidence for new `PASS`/`FAIL` records;
  validate unique property IDs and canonical ID/name pairs.
- Clarify scoped E observation coverage and preserve observed bypass failures
  even when other evidence is incomplete.
- Add a bounded accepted-evidence reference rule, synthetic fixtures, negative
  schema checks and read-only harness integrity tests.
- Replace the incomplete README snippet with a schema-valid unassessed example.
- Preserve the v0.1 specification, schema and historical AEGIS assessment.

This is an independent draft update, not a CoSAI standard or certification.
