# AEGIS 3.4.0 — issue #21 preregistration

Prepared with AI assistance for runner darklordVirtual. This is a pre-execution commitment; it contains no result or publication approval.

- Run: `aacp-aegis-340-20261013-001`.
- Frozen plan raw-byte SHA-256: `afd313c41538d54e13e8966d21a94b47a505726c7f304fa773f64d2e0632ed55`.
- Producer commit: `85e8c96887382cbe77f815a379046329379515f8` in [LortuArte/aegis-sdk](https://github.com/LortuArte/aegis-sdk/tree/85e8c96887382cbe77f815a379046329379515f8).
- [Producer scope confirmation and run authorization](https://github.com/darklordVirtual/agent-authority-conformance/issues/21#issuecomment-6135890282).
- Fixture SHA-256: `04db8c6b8f655566ae356b03967833ae9fe3fcdb47a237224dabc6295fc2731a`.
- Selected PyPI wheel: `aegis_core_lortuarte_sdk-3.4.0-py3-none-any.whl`, SHA-256 `70691ffa689dce033b1488d975aec90b63fc7f2700ad973558cbae46de61921c`.
- Interpreter: Python 3.12.14; dependencies: cryptography 50.0.2, cffi 2.1.1, pycparser 3.11. All wheel hashes are frozen in the private plan and lockfile before execution.
- Runner methodology revision: `28ce126827fd30426d602a2c4ef30a77ca75c304`.

## Procedure and boundary

Verify pins, install wheels offline in a fresh venv with required hashes, execute the unchanged fixture outside the producer checkout as an unprivileged user with a minimal environment and a timeout. Capture raw stdout, stderr, import origin, environment and actual Python exit status directly, without a `tee` pipeline. Compare against the frozen expectation: 100 presentations of one stable logical ID in one process, one fresh execution grant, 99 cached replays, one simulated downstream invocation and balance `0.000000`.

The ceiling is REPRODUCTION / BCR-1 at most. The fixture has no start barrier. This establishes no simultaneous-start guarantee, multi-process protection, live settlement, external-effect verification, independent implementation, certification or adoption. Local execution is not network isolation.

The current lab verification engine consumes JSON artifacts and does not implement wheel execution. This pilot uses an operator-controlled manual capture procedure; it must not be presented as a completed `conformance.lab` lifecycle run.

Results remain private until factual review and separate publication approval. No changes to the historical AEGIS assessment or producer implementation are made by this preregistration.
