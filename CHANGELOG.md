# Changelog

## Unreleased

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
