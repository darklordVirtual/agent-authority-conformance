# AEGIS issue #21 — follow-up preregistration 002

AI-assisted operator preparation for darklordVirtual. No execution result is published by this record.

Run `aacp-aegis-340-20261013-002`; frozen plan SHA-256 `a2b76a441de2e8f3f43cb781f6ffeb73b6aa7482bd89d7b279ec988697b609eb`.

This is a new run identity. The first plan and its setup-error attempt are preserved. Only the runner launch procedure changes: the existing restricted runtime has exactly one mapped identity (UID/GID 0), no Linux capabilities (effective, permitted and bounding sets zero), NoNewPrivs=1 and Seccomp=2. Use that existing identity without attempting setuid or privilege escalation. Record these constraints before execution; use isolated Python, fresh venv and temporary cwd, minimal environment without credentials, offline hash-required wheel installation, timeout and direct stdout/stderr/exit capture. Local execution is not a separate per-fixture filesystem or network isolation boundary.

Producer authorization and scope remain [issue #21 comment 6135890282](https://github.com/darklordVirtual/agent-authority-conformance/issues/21#issuecomment-6135890282). User follow-up authorizes completing the runner work. Producer commit remains `85e8c96887382cbe77f815a379046329379515f8`; unchanged fixture SHA-256 `04db8c6b8f655566ae356b03967833ae9fe3fcdb47a237224dabc6295fc2731a`; AEGIS 3.4.0 wheel SHA-256 `70691ffa689dce033b1488d975aec90b63fc7f2700ad973558cbae46de61921c`. Python 3.12.14; cryptography 50.0.2, cffi 2.1.1, pycparser 3.11. Full wheel pins and expectations remain in the frozen private plan.

Expected bounded fixture: 100 presentations of one logical ID in one process, 1 fresh grant, 99 cached replays, 1 simulated downstream invocation and final balance 0.000000. No start barrier, live settlement or external-effect claim. Ceiling REPRODUCTION / BCR-1 at most. Preserve native claim result separately from reproduction comparison. No independent implementation, certification or adoption claim. Manual operator capture, not a completed conformance.lab lifecycle run. Private result delivery, factual review and separate publication approval remain required.
