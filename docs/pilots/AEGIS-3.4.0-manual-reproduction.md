# AEGIS Core 3.4.0 — manual AACP v0.3 pilot (DRAFT; not frozen)

Source proposal and agreement venue: [AACP #21](https://github.com/darklordVirtual/agent-authority-conformance/issues/21). Producer: @LortuArte. Runner: @darklordVirtual / AACP.

**Status:** preparation only. No scope agreement, run authorization, subject admission, frozen plan, AACP run or publication is implied by this draft.

## Frozen candidate source (pending producer confirmation)

- Subject: `https://github.com/LortuArte/aegis-sdk`
- Candidate full subject commit: `85e8c96887382cbe77f815a379046329379515f8` (merge of producer's external reproduction kit; must be confirmed).
- Required pinned source paths:
  - `.github/workflows/external-reproduction.yml`
  - `external_validation/AEGIS_EXTERNAL_RUN_3_4_0.py`
  - applicable license and reproduction instructions, if bundled.
- Distribution: PyPI `aegis-core-lortuarte-sdk==3.4.0`. **Resolve and freeze the specific wheel/sdist filename, sha256 and Python/platform compatibility.** A version string alone is insufficient; no artifact hash has been established in this draft.
- Candidate AACP runner revision: `28ce126827fd30426d602a2c4ef30a77ca75c304`; capture the actual tested revision on freeze.
- Python: 3.12 on Ubuntu GitHub Actions according to the producer workflow. Pin installed dependencies and record interpreter/runner image identity when possible.
- Record repo commit, source file SHA-256, wheel SHA-256, package `aegis.__version__`, `aegis.__file__`, script digest, platform, interpreter, exit status and raw stdout/stderr in runner-owned evidence.

## Single bounded claim

**Claim:** Running the producer's AEGIS 3.4.0 fixture using the pinned package inside one Python process, with one stable `tool_call_id` and 100 thread-pool requests using the same economic parameters, produces exactly one `execution_permitted=True` grant, 99 responses flagged `cached=True`, exactly one *simulated* downstream invocation and a ledger balance numerically equal to zero.

The test uses `ThreadPoolExecutor(max_workers=100)` **without a start barrier**; it tests 100 requests presented through a pool, not guaranteed simultaneous entry to the authority gate. Preserve this distinction in any report.

Not established: independent implementation/verifier, distributed or multiprocess concurrency, process restart persistence, crash recovery, payment/settlement, actual external effects, alternative execution-path non-bypassability, arbitrary arguments binding, broad authority/semantic correctness, certification, adoption, or all A–G properties.

Provisional method label: **BCR-1 / REPRODUCTION at most** (AACP independence: `REPRODUCTION`). If runner does not complete the procedure, do not label it BCR-1. This run uses producer-owned source and test logic. No independent-implementation claim.

## Test procedure and result semantics

1. Confirm the offered source commit and obtain the immutable PyPI distribution with an expected SHA-256. Abort on mismatch before execution.
2. Prepare a clean, unprivileged environment with no payment credentials and no live downstream services; restrict egress after dependency acquisition where supported. Capture install provenance and import path.
3. Run the pinned script without changing its assertions or expected measurements. Use `set -o pipefail` before any `| tee` pipeline or save stdout/stderr directly; do not replace the Python process exit code with a successful `tee` exit.
4. Capture all raw outputs, exit code and environment. Compare the numeric observations and independently check the reported counts against the exposed receipts where instrumentation permits; otherwise mark this limitation explicitly.
5. AACP classification is per bounded claim: `ESTABLISHED`, `CONTRADICTED` or `NOT_ESTABLISHED` when a procedure completes; `ERROR`/`UNSUPPORTED`/`INVALID_INPUT` are non-verdicts. A run of the producer's PASS check alone is not an independent verifier.
6. Once an AACP delivery package exists, a *separate* package rerun may yield `REPRODUCED`, `DIVERGED` or `NOT_REPRODUCIBLE`. These must not be used as substitutes for the claim classification.
7. Preserve AACP manual-track consent, pin, freeze/plan-hash preregistration, input admission, run, package, private share, factual review, and unanimous post-delivery publication consent. Draft/unreleased results are not public evidence.

## Roles and next gates

**AEGIS / @LortuArte**
- Confirm the candidate full SHA, fixture paths and the intended *100 presentations (not barrier-synchronized)* claim.
- Review the single-claim scope and explicitly grant `scope_agreed` and `run_authorized` in #21 (and any agreed conditions). Review the private package; publication approval is a separate act.
- Optionally provide a PyPI distribution filename and sha256, but the runner must verify it independently.

**AACP / @darklordVirtual**
- Convert this draft to a schema-valid `templates/scopes/` manual scope with exactly one verification claim, pinned input(s), runner-owned verifier and explicit `reads_fields`. Do not give producer expectations to the verifier before it records results.
- Resolve/verify all hashes; implement the minimum subject-to-run adapter where required by the existing lab, with a safe runner-controlled execution bridge. **The current AACP verification engine reads JSON inputs and does not inherently execute a PyPI package.** Do not describe a green CI workflow as an AACP v0.3 verification run without adapting and checking the runner path.
- Add at least one inert/negative control for the runner's interpretation (for example a *deliberately modified output fixture*, without altering the pinned producer package). Distinguish the control's failure-detection capability from the subject's property verdict.
- Freeze only after both parties' consent, and publish the plan hash before execution. Run on infrastructure controlled by the AACP operator, package and deliver privately; wait for both publication approvals.

## Ready-to-run checklist

- [ ] Exact producer commit confirmed
- [ ] Package distribution and SHA-256 pinned by runner
- [ ] Schema-valid manual `SCOPE.json` and runner-owned check prepared
- [ ] Producer and runner scope agreement and run authorization recorded
- [ ] Run plan frozen/hash preregistered and input admitted
- [ ] AACP-operated reproduction with raw result/exit/environment captured
- [ ] Private delivery and factual review completed
- [ ] Separate publication approval from every named approver

Never infer successful reproduction from the producer's reported PASS.
