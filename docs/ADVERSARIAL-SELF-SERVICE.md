# Portable adversarial self-service

AACP ships a vendor-neutral adversarial suite for three bounded properties:

- **C — Exact-Call Integrity**
- **F — TOCTOU Resistance**
- **G — Effect Verification**

The suite is designed for a project maintainer to run locally against their own implementation without changing AACP and without embedding producer-expected answers in the adapter.

## Quick start

List the full machine-readable vectors:

```sh
aacp adversarial --list --json
```

Copy the adapter template:

```sh
cp templates/adapters/portable-cfg-adapter.py ./aacp_adapter.py
```

Map each case kind to the implementation under test, then run all portable probes:

```sh
aacp adversarial --adapter ./aacp_adapter.py:run_case
```

Run only one property:

```sh
aacp adversarial --adapter ./aacp_adapter.py:run_case --property C
aacp adversarial --adapter ./aacp_adapter.py:run_case --property F
aacp adversarial --adapter ./aacp_adapter.py:run_case --property G
```

CI-friendly strict mode fails if any selected case is contradicted, unsupported, invalid, errored or inconclusive:

```sh
aacp adversarial \
  --adapter ./aacp_adapter.py:run_case \
  --property C --property F --property G \
  --require-supported
```

JSON output is available with `--json`.

## Adapter contract

The adapter exports one callable:

```python
def run_case(case: dict) -> dict:
    ...
```

A case contains:

- `id`
- `property`
- `kind`
- `title`
- `challenge`
- `claim_ceiling`

It deliberately contains no expected result, verdict or pass/fail bit.

The adapter reports observations only. AACP owns the classification.

### `exact_call`

Arrange authority for `challenge.authorized_call`, then present the changed call at the named mutation phase.

Return either:

```json
{"execution":"COMPLETED","outcome":"REFUSED"}
```

or:

```json
{
  "execution":"COMPLETED",
  "outcome":"EXECUTED",
  "executed_call":{"tool":"...","arguments":{},"tenant":"...","target":"..."}
}
```

AACP establishes the bounded C case only when the changed call is refused or the actually executed call is exactly the authorized call.

### `freshness`

Authorize under `authorized_context`, move the load-bearing state to `dispatch_context`, then attempt the action.

Return `REFUSED` or `EXECUTED`.

These cases cover revocation, tool-definition drift, callable drift, policy revision, fresh hard guards and capability epochs. They do not prescribe how an implementation represents those concepts internally.

### `effect_compare`

Apply the supplied postcondition contract to the supplied observation.

Return an effect status, for example:

```json
{"execution":"COMPLETED","effect_status":"EFFECT_MISMATCH"}
```

For a structurally invalid contract, report a completed rejection:

```json
{"execution":"COMPLETED","outcome":"INVALID_INPUT"}
```

Do not convert an adapter crash into a property failure; use `ERROR` or allow the runner to record the exception as a non-verdict.

### `receipt`

Submit the supplied effect receipt against the supplied server-owned lineage and report:

```json
{"execution":"COMPLETED","outcome":"ACCEPTED"}
```

or `REFUSED`.

### `receipt_sequence`

Submit both supplied receipts in order and report both outcomes. This is used to distinguish an unresolved report from a terminal-slot poisoning failure.

## Result semantics

Per case, AACP emits:

- `ESTABLISHED`
- `CONTRADICTED`
- `NOT_ESTABLISHED`

or a non-verdict execution state:

- `UNSUPPORTED`
- `INVALID_INPUT`
- `ERROR`

There is no aggregate score and no "N of M conformant" result.

The run record is always labelled `SELF_RUN`. A successful local run does **not** establish independent reproduction, production security, certification or Federation adoption.

## Relationship to Federation tracks

This command is intentionally separate from Federation self-service offers.

`aacp adversarial` may execute a subject-owned adapter because the subject maintainer is running it locally. Federation self-service verification remains runner-owned and does not execute producer code.

The same neutral challenge semantics can later be placed in a frozen manual or independently implemented lab run. Independence is recorded by that run, not inferred from this local command.

## Current portable cases

The first suite contains:

**C**
- nested argument mutation
- nested key deletion
- scalar-kind substitution
- verify-then-mutate

**F**
- revocation after approval
- tool-definition drift
- callable drift
- policy revision drift
- fresh hard-guard activation
- capability-epoch advance

**G**
- missing field versus explicit null
- unknown comparison rule
- rule for undeclared field
- forged tool identity in effect evidence
- forged tool-definition identity
- contradictory terminal status/reason
- unresolved receipt terminal-slot poisoning

The cases were selected because they discriminate implementation-independent safety semantics. Backend selection, product-specific readiness checks and implementation-specific class names are intentionally excluded.
