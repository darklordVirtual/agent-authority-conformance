# REMORA control inspection

Executed on 2026-11-08 against
[REMORA-research](https://github.com/darklordVirtual/REMORA-research) `dev` at
`06c2f8f038d9d24668158ce24cbd444e89fd306a`, with AACP control catalog
v1.2.0. The purpose is to check whether REMORA has the weaknesses the catalog
names, and to give the maintainer what is needed to fix any it has.

- **Generated report:** [`reports/remora-06c2f8f/REPORT.md`](../reports/remora-06c2f8f/REPORT.md)
- **Assessment (schema v0.1):** [`examples/remora-06c2f8f.json`](../examples/remora-06c2f8f.json)
- **Binding and probes:** [`controls/bindings/remora-06c2f8f/`](../controls/bindings/remora-06c2f8f/)
- **Result record:** [`reports/remora-06c2f8f/results/`](../reports/remora-06c2f8f/results/)

This is a **self-assessment**. The AACP maintainer is REMORA's author; the
probes were drafted and executed by an AI agent and reviewed by the maintainer.
The catalog's status rules apply unchanged, with one addition made for this
binding: every probe that did not find its weakness had to be shown
**sensitive**, meaning that with the protection removed it does find it. A
"not observed" from a probe that could not have observed anything is
reported as such, never as a protection that held.

## Result

| Property | REMORA |
| :--- | :--- |
| A Receipt Integrity | UNTESTED; 4 controls not observed, all sensitive |
| B Authority Provenance | UNTESTED; 4 controls not observed, all sensitive |
| C Exact-Call Integrity | UNTESTED; 1 control not observed, sensitive |
| D Semantic Authority | UNTESTED; 3 controls not observed, all sensitive |
| E, F, G | UNTESTED, no probes |

None of the catalog's A-D weaknesses reproduces in REMORA. That is
`UNTESTED`, not `PASS`: AACP controls never yield PASS, because a set of
probes failing to find a weakness is not direct evidence that a property
holds (SPECIFICATION §3, §5). What it does establish is narrower and
checkable: for each probed weakness, REMORA refuses it, and removing the
named protection makes the same probe succeed.

REMORA has **three reproduced defects outside A-G**, all in audit and evidence
integrity:

| # | Control | Where | Severity | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | AACP-X-04 | `remora/adapters/audit/jsonl.py` | Medium | OBSERVED, repair discriminates |
| 2 | AACP-X-01 | `remora/governance/tenant_chain.py`, `SQLiteTenantChain` | Medium | OBSERVED, repair discriminates |
| 3 | AACP-X-02 | `remora/assurance/merkle.py` | Low | OBSERVED (two ways), repairs discriminate |

## Findings to fix

### 1. JSONL audit log never verifies after a reload (AACP-X-04)

**Where.** `remora/adapters/audit/jsonl.py`. `append()` hashes the entry with
`metadata = {**entry.metadata, "oracle_count", "verdict", "policy_version"}`
(lines 81-86) but writes `"metadata": entry.metadata` without those three
keys (line 97). `_load_existing_chain()` (line 49) rebuilds each
`HashChainEntry` from the written metadata, so every recomputed hash differs.

**Effect.** `JSONLAudit(path).verify()` returns `False` for every log written
and reloaded, untouched or not. An integrity check that always fails cannot
distinguish tampering from nothing, and a restart turns every honest log into
a reported break. Used by `remora/shadow/replay.py`.

**Reproduce.** `aacp_probes/test_remora_probes.py::test_x04_jsonl_audit_intact_log_fails_after_reload`.

**Fix (recommended, backward compatible).** Rebuild the hashed metadata on load
from the fields already in each record, so logs written by the current code
verify too:

```python
# remora/adapters/audit/jsonl.py, in _load_existing_chain()
metadata = {
    **record.get("metadata", {}),
    "oracle_count": record["oracle_count"],
    "verdict": record["verdict"],
    "policy_version": record["policy_version"],
}
entry = HashChainEntry(..., metadata=metadata)
```

Checked against a log written by the current code: with this change the
untouched log verifies, and editing a record is detected. The repair AACP uses
to show discrimination (`R-X-04`, persisting `chain_entry.metadata` on write)
also works, but only for logs written after the change.

**Regression test.** Write three entries, reload, assert `verify()`; then edit
one record, reload, assert not `verify()`.

**Note.** Once this is fixed, the JSONL log is exposed to finding 2 as well:
`AuditHashChain` keeps no head, so deleting the last line still verifies
(checked). Anchor it as in finding 2.

### 2. Durable SQLite audit chain does not detect tail truncation (AACP-X-01)

**Where.** `remora/governance/tenant_chain.py`. `PostgresTenantChain` keeps
`tenant_chain_head` and exposes `stored_head()` (line 658), and
`_verify_generic` reports `stored_head_mismatch`. `SQLiteTenantChain`
(line 437), the single-node durable backend selected by `REMORA_CHAIN_DB`, has
no head table in `_SQLITE_DDL` (line 260) and no `stored_head()`, so
`verify()` has nothing to compare the last entry with.

**Effect.** Deleting the newest entries from the SQLite file leaves a chain
that verifies. Detection then depends on an `expected_head` supplied from
outside, which no caller in the execution path passes.

**Reproduce.** `test_x01_sqlite_chain_tail_truncation_undetected`.

**Fix.** Give SQLite the Postgres contract: create `tenant_chain_head` in
`_SQLITE_DDL`, upsert it in `_insert` inside the same `BEGIN IMMEDIATE`
transaction, and add `stored_head()`. The repair `R-X-01` in the binding is a
minimal version of exactly this and makes the probe stop observing.

**Limit of the fix.** A head stored in the same database is defeated by an
attacker who also edits the head. For that case, anchor the head outside the
store, for example by exporting a signed root with `remora/audit/merkle.py`
(`sign_root`, `export_daily_root`) and passing it as `expected_head`. The
probe contract leaves the stored head alone, so it tests the first property only.

**Regression test.** Append three entries, delete the newest row, assert
`verify()` reports `stored_head_mismatch`.

### 3. Assurance Merkle tree is ambiguous (AACP-X-02)

**Where.** `remora/assurance/merkle.py`. The odd node is duplicated (line 57),
so `[a, b, c]` and `[a, b, c, c]` share a root. Leaves (`_h(item)`, line 52) and
nodes (`_pair`, line 18) share one hash domain, so an internal node's preimage
verifies as a leaf with a shorter proof.

**Effect.** Low in the current code. The tree is used by `AssuranceTrace`
(`remora/assurance/trace.py`), which is opt-in (`enable_assurance_trace` /
`enable_zkp_assurance`) and also records `leaf_count` beside the root
(`reporting.py`, `AssuranceEnvelope`). A consumer that compares root and count
together tells the two sets apart. Nothing outside the module calls
`verify_inclusion`. The audit chain uses `remora/audit/merkle.py`, which is
correct by default (probe P-X-02c, not observed, sensitive).

**Reproduce.** `test_x02_assurance_merkle_odd_duplication`,
`test_x02_assurance_merkle_node_as_leaf`. The first was also reported by a
ChatGPT pre-probe on `master` 53b1f45; the files are byte-identical on `dev`.

**Fix.** Use the construction `remora/audit/merkle.py` already uses:
`SHA-256(0x00 || leaf)`, `SHA-256(0x01 || left || right)`, odd node promoted
unchanged. `proof()` must then skip a level where the node was promoted.
Roots change, so bump `signature_standard` (for example
`REMORA-Assurance-Trace-v2`) rather than silently reinterpreting old traces.
The binding's repairs `R-X-02a` (promotion) and `R-X-02b` (node domain) each
remove one of the two observations.

## Verified protections

Each of these was probed with the catalog weakness, refused, and then
shown sensitive by removing the named protection. Line references are at the
pinned revision.

| Control | Probe | Protection the weakening removed |
| :--- | :--- | :--- |
| A-01 use limit over restart | P-A-01 | durable consumed-jti ledger (`gate.py`, SQLite/Postgres/D1; production refuses in-memory) |
| A-02 revocation fails closed | P-A-02 | `AtomicAdmission._refuse_revoked` refuses when the store cannot answer (`admission.py:360-373`) |
| A-03 untrusted signer | P-A-03 | v3 Ed25519 verification against configured keys only (`token.py:692-722`) |
| A-04 replay | P-A-04 | **two layers:** consumed-jti ledger and the outbox's refusal to re-claim a settled dispatch (`outbox.py:219`) |
| B-01 unauthenticated principal | P-B-01 | bearer required; tenant and role from the credential table (`api.py`) |
| B-02 unprovisioned credential | P-B-02 | unknown bearer refused with 401 |
| B-03 token used by another principal | P-B-03 | signed authorization context binds the principal (`token.py:745-757`) |
| B-04 self-approval | P-B-04 | `SeparationOfDutiesRefused` when distinct approvers are required, always in production (`review_service.py`) |
| C-01 token for another call | P-C-01 | **three layers:** service binding check (`service.py:2384`), token observation hash, signed context |
| D-01 value type and unit | P-D-01 | exact integer scaling (`cumulative_limits.py:225-235`); unknown unit refused as `UNDECLARED` |
| D-02 resource escape | P-D-02 | canonical resources with segment-bounded matching (`capabilities/resource.py`) |
| D-03 effect without ACCEPT | P-D-03 | **two layers:** service `not_accept` and gate `ACCEPT_ACTIONS`; no file is written |
| EV-02 evidence vs commit | S-EV-02 | attestation workflow compares the attested commit with the workflow's commit |
| EV-03 stale re-seal | S-EV-03 | generator always runs the suite; no reuse mode |
| EV-05 hard-coded totals | S-EV-05 | totals parsed from the pytest summary |

Several of these were sensitive only once **every** layer was removed. That
is defence in depth, and the binding records it in the weakening text. It
also means a regression in one layer would not show up as an AACP finding
until the other layers regressed too, so REMORA's own tests should keep
covering each layer separately.

## Observations that are not findings

- **Unsigned test attestation.** `artifacts/credibility-pack/test-attestation.json`
  is produced in CI but not signed; its authority is the Actions run, and
  anyone can produce a file with `gate: PASS` locally. `release.yml` already
  uses `actions/attest-build-provenance`; doing the same in
  `.github/workflows/attestation.yml` gives the attestation a verifiable signer.
  (Recorded under AACP-EV-04 as not applicable: there is no key to misuse.)
- **Replay with a lost ledger surfaces as a 500.** With the jti ledger removed
  (the weakening, or an in-memory ledger after a restart in development), the
  outbox still blocks the replay, but by raising an unhandled `ValueError`
  rather than a 409. Production refuses an in-memory ledger, so this is a
  robustness note, not a bypass.
- **Not exercised:** `PostgresTenantChain` (it keeps and checks a head), the
  D1 state endpoint, the MCP server and the edge workers. `ARCHITECTURE.md`
  §5.4 states that some workers are open when no secret is configured; that
  is outside these probes.

## Not applicable

AACP-X-03 (REMORA has no peer key exchange), AACP-EV-01 (no suite-transcript
digest is published) and AACP-EV-04 (the attestation carries no key; see above).

## Reproduce

```sh
git clone https://github.com/darklordVirtual/REMORA-research remora
git -C remora checkout 06c2f8f038d9d24668158ce24cbd444e89fd306a
python -m conformance.controls run --binding controls/bindings/remora-06c2f8f --subject remora \
    --out out/result.json --run-id my-run --operator "<you>" --independence REPRODUCTION
python -m conformance.controls compare reports/remora-06c2f8f/results/$(cat reports/remora-06c2f8f/CURRENT) out/result.json
```

The run installs REMORA with its `api`, `security` and `interop` extras into
the running interpreter and executes REMORA code, so use a disposable
environment. After a fix lands on `dev`, a new binding pinned to the new
commit (same probes, updated file pins) shows each finding's probe no longer
observing, with its repair no longer needed.

## Boundaries

Self-assessment; probes and weakenings are the assessor's; no independent
review. Development environment with emulated production rules where noted;
ACCEPT tokens minted directly, as REMORA's own tests do. E, F and G have no
probes in either binding. A weakening shows a probe is sensitive to one
removal; it does not show the protection is complete.

## After the fix (b5e4c42)

The text above records the run against `06c2f8f` and is kept as it was. REMORA
fixed the three findings on branch `fix/aacp-x01-x02-x04`, commit
`b5e4c42509c856c297d6a79210394ecbe90a05a4` (not yet merged to `dev`). A new
binding, [`controls/bindings/remora-b5e4c42/`](../controls/bindings/remora-b5e4c42/),
runs the same catalog and the same probe file against it; the `06c2f8f`
binding, report and result are unchanged.

- **Generated report:** [`reports/remora-b5e4c42/REPORT.md`](../reports/remora-b5e4c42/REPORT.md)
- **Assessment (schema v0.1):** [`examples/remora-b5e4c42.json`](../examples/remora-b5e4c42.json)

| Probe | `06c2f8f` | `b5e4c42` | Weakening that makes it observe again |
| :--- | :--- | :--- | :--- |
| P-X-01 | OBSERVED, repair discriminates | NOT_OBSERVED, sensitive | W-X-01: `stored_head()` returns nothing |
| P-X-02a | OBSERVED, repair discriminates | NOT_OBSERVED, sensitive | W-X-02a: v2 duplicates the odd node |
| P-X-02b | OBSERVED, repair discriminates | NOT_OBSERVED, sensitive | W-X-02b: v1 is the default again |
| P-X-04 | OBSERVED, repair discriminates | NOT_OBSERVED, sensitive | W-X-04: reload uses the written metadata |

The other 16 probes give the same result on both revisions. Before the new run
the `06c2f8f` binding was re-run on the pinned revision as a `REPRODUCTION`
and compared with the recorded result: `same_findings: true`.

P-X-02b is refused by three v2 layers at once (domain prefixes, raw-digest
node input and a mandatory `leaf_count`), so its weakening has to remove all
three. REMORA's own tests remove each alone.

What did not change: NOT_OBSERVED is not PASS and every A-G row stays
UNTESTED. The run is `AUTHOR_RUN` by the person who wrote the fix. Two gaps
remain: a stored head in the same database does not stop an attacker who
rewrites the whole file, and the JSONL log keeps no head at all (REMORA SDD
`docs/design/aacp-audit-integrity-remediation-sdd-v1.md`, R1 to R3).
