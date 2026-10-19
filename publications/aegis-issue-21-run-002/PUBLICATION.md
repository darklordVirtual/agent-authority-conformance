# AEGIS Core 3.4.0 — bounded Run 002 publication

Publication recorded: 2026-10-19. Publication authorization received: 2026-10-18.
AACP issue: https://github.com/darklordVirtual/agent-authority-conformance/issues/21
Run ID: `aacp-aegis-340-20261013-002`.
Classification ceiling: **REPRODUCTION / BCR-1 at most**.

LortuArte authorized publication of the bounded Run 002 report, the exact corrected wheel-free review archive, and a factual summary in issue #21 after reviewing the documentation corrections. This dated note records that authorization separately from the frozen evidence. The private correspondence itself is not published.

## Approved artifacts

- [Exact corrected wheel-free review archive](AEGIS-issue-21-private-review-corrected-2026-10-15.zip) — SHA-256 `cb26a043952a7c399f89e023561b04b27b0be0907a2a10123379be127abbd490`.
- [Run 002 report](REPORT.md) — an exact, unchanged extraction of the reviewed archive's `REPORT.md`; SHA-256 `717e0104ed5b0c153b6756101ab7ea84049e1a26ed13157a07452a55a34e6574`.

The ZIP's 22 integrity-manifest entries were checked against the actual bytes before publication. It contains the frozen plan, fixture, raw observations, capture, lockfile, license, integrity manifest, and preserved Attempt 001 setup-error record. No binary wheels are included. The separate wheel-inclusive private evidence archive and private correspondence are excluded from publication.

## Bounded observations

| Observation | Result |
|---|---:|
| Presentations of one stable logical action | 100 |
| Fresh execution grants | 1 |
| Cached replays | 99 |
| Simulated downstream invocations | 1 |
| Final balance | `0.000000` |
| Frozen fixture expectation comparison | `REPRODUCED` |
| Bounded fixture claim | `ESTABLISHED` |

This was an **operator-controlled manual reproduction of a producer-authored fixture in one process**, using 100 worker threads without a start barrier. There was **no guaranteed simultaneous start**. The downstream invocation was a **simulation**; no real external economic effect was verified.

It does **not establish** independent implementation, independent verification of a general AEGIS property, certification, production validation, production adoption, live settlement, external-effect verification, multiprocess guarantees, distributed exactly-once execution, crash recovery, or completion of the full conformance.lab lifecycle. There is no automatic A–G credit, no upgrade of the historical AEGIS assessment, and no broader AEGIS verdict.

`REPRODUCED` here means comparison with the frozen fixture expectations; it does not assert that a `rerun.py` package rerun was performed. `ESTABLISHED` applies only to this bounded fixture claim.

## Pins and preserved history

- Producer commit: `85e8c96887382cbe77f815a379046329379515f8`.
- Preregistration: https://github.com/darklordVirtual/agent-authority-conformance/commit/00de75cee0141339e631924e2a3ca75d5e71483a.
- Frozen plan SHA-256: `a2b76a441de2e8f3f43cb781f6ffeb73b6aa7482bd89d7b279ec988697b609eb`.
- Fixture SHA-256: `04db8c6b8f655566ae356b03967833ae9fe3fcdb47a237224dabc6295fc2731a`.
- AEGIS distribution SHA-256: `70691ffa689dce033b1488d975aec90b63fc7f2700ad973558cbae46de61921c`.

The report and archive retain their October 15 preapproval wording, including `PUBLICATION_NOT_APPROVED`; the capture retains `publication_state=PRIVATE_NOT_REVIEWED`. These describe historical states and are intentionally unchanged. Current publication authorization is recorded only in this separate dated note. Attempt 001 remains `SETUP_ERROR` before AEGIS import, with no claim verdict. This publication is not a new run or a retroactive conformance.lab lifecycle completion.

## Follow-up

The public record is available for LortuArte to check against the approved scope. Post-publication producer verification has not yet been recorded; it must not be implied. The October 18 authorization already permits this bounded publication; no further run or broader classification is required to cite it accurately.

AEGIS producer-authored fixture and distribution: copyright 2026 Iraitz (Lortu) / AEGIS, MIT; upstream license preserved inside the archive. AACP methodology: Apache-2.0. Publication prepared with AI assistance for darklordVirtual.
