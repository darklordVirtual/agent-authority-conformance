# Federation adapters

Adapters are read-only evidence resolvers for bounded cross-project reviews. They
are intentionally thinner than AAC itself.

An adapter MAY locate pinned artifacts, verify exact bytes, normalize provenance
and prepare named claim inputs. It MUST NOT award A-G credit, execute arbitrary
code from the subject repository by default, convert missing evidence into a
failure, publish a maintainer's review without the agreed release gate, or imply
endorsement.

The pipeline is:

```text
producer artifact -> adapter resolution -> evidence admission -> AAC inference
                  -> maintainer review -> publication decision
```

Each arrow is a claim boundary. Resolution proves only that the assessor read the
declared bytes. Admission additionally asks whether those bytes are relevant,
authentic enough for the procedure, applicable to the scope and sufficiently
independent. Only then may a property-specific AAC procedure infer a bounded
result.

## Required manifest discipline

Every adapter manifest pins a full producer commit, artifact SHA-256 values,
source classes, a claim ceiling, explicit non-claims, and a mandatory maintainer
review gate. Expected PASS/FAIL verdicts are forbidden in adapter claim input.

For third-party projects, create an adapter only from public artifacts or with
the maintainer's permission. Freeze subject revision, adapter revision, inputs,
procedure and publication rules before the first evaluative run.

See `docs/FEDERATION-REVIEW-PROTOCOL.md`.
