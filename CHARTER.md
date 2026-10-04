# Charter

Agent Authority Conformance Profiles (AACP) is an implementation-neutral set
of falsifiable profiles for evaluating bounded authority-to-effect properties
in agent systems. Bounded Claim Reproduction (BCR) is the evidence method its
results are recorded in. This charter binds both.

## Seven principles

1. **Implementation neutrality.** No implementation has a privileged position.
   A profile MUST NOT grant privileged semantics, expected outcomes, trust or
   evaluation paths to REMORA or to any other originating implementation.
   After a profile is published, the project that contributed it is one
   implementation under test like every other.
2. **Project sovereignty.** Conformance evidence gives this project no control
   over the implementation it describes, and gives the implementation no
   control over the profile.
3. **Bounded claims.** Every result is about one explicit property under one
   profile revision. A result says what it establishes and what it does not.
4. **Falsifiability.** A claim without a defined failure condition is not an
   AACP profile. Every profile carries negative and mutation fixtures that a
   non-conforming implementation would fail.
5. **Reproducibility.** Every result binds the profile revision, the fixture
   digests, the evaluator revision, the implementation revision and the
   environment, so a third party can repeat the run.
6. **Non-transitivity.** A result on property A establishes nothing about
   property B. Properties are not aggregated into a score.
7. **No implied endorsement.** Reproduction, interoperability or conformance
   evidence implies no endorsement, membership, trust or certification.

## What AACP is not

AACP is not a certification body, a product ranking, a security grade or a
Federation protocol. It does not issue project-level verdicts. The
[LF Decentralized Trust Agent Authority Conformance lab](TERMINOLOGY.md#names)
is a separate, neutral venue; AACP profiles and BCR records are written so
they can be contributed to such a venue, and this project does not compete
with it.
