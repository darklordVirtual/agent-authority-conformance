# REMORA evidence-sufficiency v1 adapter exercise

This is deliberately a **resolution-only metatest**, not a REMORA assessment.

The subject pin and two artifact hashes are the frozen inputs agreed for the
seeded-fault adequacy experiment in REMORA issue #629. The adapter demonstrates
that AAC can consume a foreign repository through immutable bytes without
granting that repository A-G credit.

Why REMORA is useful here: its evidence-sufficiency suite explicitly separates
runtime outcome, authored case result and evidence verdict, and documents a
synthetic-premise trust boundary. Those constraints are useful adversarial tests
for AAC's own evidence model.

A successful resolution establishes only byte identity for the two pinned
artifacts. The adequacy result remains a separate corpus-adequacy experiment.
Current REMORA maturity and numerical claims must be read from REMORA's current
claim and capability registers before any broader statement is made.

## Reproduction

Clone REMORA at the exact subject SHA, then from AAC run:

```python
from conformance.adapter import load_manifest, resolve
m = load_manifest("adapters/remora-evidence-sufficiency-v1/adapter.json")
print(resolve(m, "/path/to/REMORA-research"))
```

The committed manifest pins the resolver implementation revision used by this exercise. Before any later public run, freeze the exact subject, adapter, manifest and procedure revisions together and record the resulting manifest hash.
