# Migrating assessments to v0.2

Migration is opt-in. These existing paths and their semantics remain v0.1:

- `SPECIFICATION.md`
- `schema/assessment.schema.json`
- `examples/aegis-core-3.4.0.json`

Consumers MUST choose a schema by `spec_version`. The old schema URL has not
been redirected or broadened. Validate new records with
`schema/assessment-v0.2.schema.json` and the cross-field scope check in
`conformance.validation.validate_assessment`.

## Per-record review

1. Copy the record to a new versioned path; preserve its historical source.
2. Set `spec_version` to `0.2` and the actual new assessment date. Preserve the
   evaluated system revision unless new system evidence was inspected.
3. Resolve duplicate property IDs and incorrect ID/name combinations.
4. Review each row using the table below. Add the actual procedure, pinned
   evidence, evaluation scope and unresolved obligations where required.
5. For an E `PASS`, supply topology, observation-coverage and bypass artifacts
   for the same scope. Without sufficient evidence, complete the assessment
   with the applicable unresolved obligations; do not invent a coverage claim.
6. Run the validation commands in the README and review the evidence itself.

| v0.1 row | v0.2 treatment |
|---|---|
| `PASS` / `FAIL` | Retain only after confirming a completed applicable procedure, sufficient resolved references and the tested scope. |
| `UNTESTED`, procedure never run | `verification_status: NOT_RUN`, `status: UNTESTED`. |
| `UNTESTED`, procedure ran but could not decide | `COMPLETED` + `NOT_ESTABLISHED`, naming unresolved obligations. |
| `OUT_OF_SCOPE` | `NOT_RUN` + `OUT_OF_SCOPE` for an explicit non-claim; preserve any prior demonstrated violation separately. |
| Unsupported procedure | `UNSUPPORTED` + `status: null`, with a structured error. |
| Malformed input | `INVALID_INPUT` + `status: null`, with a structured error. |
| Verifier failure | `ERROR` + `status: null`, with a structured error. |

Do not globally rename `UNTESTED` to `NOT_ESTABLISHED`. The old status did not
record whether applicable verification ran. Do not infer execution status from a
runtime success, receipt-chain result or passing fixture harness.

The v0.2 validator checks format and selected consistency rules. It cannot
automatically decide that a revision is immutable, an artifact is trustworthy,
or a scoped security property actually holds. That remains evidence review.

## Compatibility checks

CI retains the v0.1 validation job and adds v0.2 checks separately. A regression
test pins the Git blob hashes of the three legacy files above. It detects
accidental historical rewrites; schema tightening is confined to the new path.

External test repositories, published vectors and their expected results are
not changed by this migration. Consumers can continue using v0.1 until they
explicitly adopt v0.2.
