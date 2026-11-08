# Unresolved research questions

**Status:** non-normative. Each question stays open until a decision is recorded with its
evidence. A profile may proceed with a question open only if its claim ceiling excludes what
the question leaves uncertain.

| ID | Question | Why it matters | Affects | Current handling |
|---|---|---|---|---|
| RQ-01 | Can a pure evaluation over admitted evidence establish atomic shared accounting, or only that no oversubscription occurred under the exercised schedules? What evidence would support the stronger claim (a recorded concurrent history checked for linearizability, a design argument, fault injection)? | H2 as written asks for atomicity; an observed history cannot prove it for unexercised schedules | cumulative limits | Draft claim and ceiling limited to the observed history (DRAFT-CLAIMS §1) |
| RQ-02 | What counts as a "bounded, authenticated resolution" of an unknown outcome? | H4 releases a reservation only on such evidence; without a definition the rule is untestable | cumulative limits | Open; H-NEG-03 tests only that restart or time alone does not release |
| RQ-03 | Distinct approver identities versus distinct humans: is any evidence of distinct persons in scope? | Several identities on one host prove nothing about people | cumulative limits | Out of scope; stated in the ceiling |
| RQ-04 | What minimal trust-material record makes a key trusted for an issuer, domain and time without live services (signed tag, DID document snapshot, transparency log proof)? | I3; an in-package key proves internal consistency only | cryptographic integrity | Trust material is runner-owned; how it was obtained is recorded |
| RQ-05 | May the reference evaluator use a pure-Python, verification-only Ed25519 tested against RFC 8032 (as the PR #24 NTI example does), or must it depend on a vetted library such as pyca/cryptography? The lab vendors standard-library-only code into run packages. | Proposal I6 says not to ship home-made crypto; lab packaging says no third-party imports; both cannot hold for a vendored evaluator | cryptographic integrity; lab packaging | Open. Disclosure: the drafting agent wrote that example verifier |
| RQ-06 | How do vectors express canonicalization claims, given that the lab's canonical JSON is documented as not RFC 8785? | I2 forbids claiming JCS without compliance | cryptographic integrity | Prefer raw-byte preimage contracts |
| RQ-07 | What positive-control design makes an absence of detections meaningful, and how is attacker capability bounded so each class is falsifiable? | A blind detector cannot establish absence | agent cyber family | Observation prerequisite (ADR-0004) |
| RQ-08 | Agent behavior under injected content is nondeterministic. Are vectors recorded tool-call traces evaluated deterministically, with the collector run as a separate, repeated, preregistered experiment? | Deterministic vectors are required; model behavior is not deterministic | agent cyber family | Evaluate admitted traces; the collector is out of the evaluator |
| RQ-09 | One record type (`bcr-run-v1`) or a separate profile envelope? Does `NOT_ADMITTED` belong in profile records? | Two result systems would diverge | all | ADR-0002, ADR-0003 |
| RQ-10 | Which non-REMORA implementations can present each input contract? | Stage 5 needs one per applicable profile; none is identified | all | UNKNOWN. No project is named without its consent |
| RQ-11 | Where do profile vectors live and how are they frozen relative to `vectors/aacp-reference-vectors-v1`? | Frozen suites must not be edited; new suites need versioning | all | ADR-0002 proposes `profiles/<id>/v<n>/` with `SHA256SUMS` |
| RQ-12 | How is "agent cyber boundary" kept from being quoted as a security approval in prose, outside machine-checked fields? | AC-09 covers README and public summaries too | agent cyber family | Index category only; test that no output prints a family result |
| RQ-13 | Should AACP publish crosswalks to OWASP agentic risks, NIST SSDF or CoSAI WS4 material at all? | A mapping table can read as alignment or endorsement | all | None in this SDD; references stay background only |
