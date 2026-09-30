# Changelog

## Unreleased

- Add seeded-fault adequacy for the bounded E rule: `conformance/mutations-v0.2.json`
  defines 30 faults and two controls, `python -m conformance.mutations` scores the
  committed fixtures against them in memory, and seven fixtures were added so that
  no fault survives (one per missing minimum class, an extra attempted class, and
  every obligation open at once).
- Add `python -m conformance.invariants`: twelve metamorphic relations and a
  table-driven reference model checked against `evaluate` over an exhaustively
  generated space of accepted-evidence documents.
- Document both in `MUTATIONS-AND-INVARIANTS.md`; both run in CI.

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
