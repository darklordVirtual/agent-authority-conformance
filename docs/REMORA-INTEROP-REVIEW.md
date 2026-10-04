# REMORA interop source inspection

Inspected on 2026-10-04. This is a bounded source inspection for designing
self-service integration, not a complete audit, production assessment or
independent execution of REMORA. No REMORA code was executed.

## Sources and observations

1. [Historical checker](https://github.com/darklordVirtual/REMORA-research/blob/31c4060630923344d43d9fac26821150262c3687/conformance/evidence-sufficiency-v1/checker.py):
   `assess` restricts `premise_source` to `synthetic_fixture`. Admission,
   tested-route enforcement and postcondition inference trust explicit accepted,
   complete and scope-bound premises. It separates evidence verdict from runtime
   outcome and authored test expectation. These booleans are not a production
   evidence-admission mechanism; the code says so explicitly.
2. [Producer package code](https://github.com/darklordVirtual/REMORA-research/blob/51431a9724074ffa292c5d4dd8168f1b2c919ffd/scripts/interop_package.py):
   `package_digest` hashes sorted `<path> <sha256>\n` lines, prefixed `sha256:`.
   `check` compares file bytes, index/manifest digest and lifecycle, claim-packet
   and verifier-request pins, ceilings and native run schemas. `freeze` checks
   committed tree bytes before recording a later freeze record. Package identity
   is distinct from source provenance and the commit carrying the package.
3. [Federation contract](https://github.com/darklordVirtual/REMORA-research/blob/51431a9724074ffa292c5d4dd8168f1b2c919ffd/docs/interop/FEDERATION.md):
   the stable discovery entry is `artifacts/interop/index.json`. Native boundary
   packages cover exact-call/single-use binding, fresh authority and effect-state
   distinction. Native schemas separate implementation diversity, operator and
   host independence. Reproduction or consumption grants no authority.
   The package states and numerical/maturity claims are producer declarations,
   not independently verified by this inspection.

## Integration gaps addressed here

- There was no root agent entry point connecting roles, contracts, commands,
  falsifying checks and stop conditions. `AGENTS.md` and the self-service guide
  now supply it; Copilot's repository instructions link to that same entry.
- The local CLI returned success even for incomplete resolution. It now exits
  nonzero while preserving non-verdict semantics and writing the diagnostic bundle.
- Resolution alone lacked a packaged actual-run record and checksum inventory.
  The optional run-package mode validates the existing schemas and records
  actual procedure provenance separately from the input's historical adapter pin.
- Existing REMORA CI printed a review-pending bundle. It now withholds full
  result content; the new manual workflow gates details and uploads by policy.

## Remaining boundaries

The historical two-artifact adapter proves neither the checker semantics nor
corpus adequacy and consumes none of the newer native boundary contracts.
Those need separate versioned adapters and independent inference procedures.
REMORA's result/package schemas are not interchangeable with AACP schemas.
The source inspection did not validate every current package, run the native
test suite, authenticate premises or assess live effects. There is no automated
review/consent adjudicator or signature-based attestation service here.