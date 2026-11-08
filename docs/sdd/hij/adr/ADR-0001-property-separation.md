# ADR-0001: H, I and J are profiles with a declared A–G relationship, not properties

**Status:** PROPOSED (awaiting maintainer decision)
**Addresses:** adversarial review B-01, B-04; proposal §0, §1.1; AC-08

## Context

The proposal names three optional profiles H, I and J "on top of the existing AACP A–G
model". The governing documents constrain this:

- TERMINOLOGY.md: the A to G property model is unchanged, and a profile is identified as
  `AACP-<PROPERTY-NAME>-<revision>`.
- SPECIFICATION-v0.2.md §1: v0.2 "does not add an eighth property".
- CHARTER.md principle 6: a result on one property establishes nothing about another, and
  properties are not aggregated.
- The existing profile `AACP-OBSERVED-EFFECT-VANTAGE-1` states its relationship as
  "partial prerequisite evidence for G — Effect Verification; never a G result by itself".

Single letters following G read as properties eight to ten. A reader then sees "A–J", and
a summary such as "10/10" becomes possible, which proposal decision 2 itself forbids.

## Decision (proposed)

1. The three proposals are **profiles**. They add no property to the A–G model.
2. Their identifiers follow TERMINOLOGY.md:
   - `AACP-CUMULATIVE-AUTHORITY-LIMITS-1`
   - `AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY-1`
   - `AACP-AGENT-CYBER-BOUNDARY-<CLASS>-1`, or one identifier, depending on ADR-0004
3. The letters H, I and J are informal handles used only in the SDD and these review
   documents. They do not appear in any schema enum, record, file name, CLI output or
   README summary. A validator refuses `H`, `I` or `J` as a profile identifier.
4. Each profile carries an **A–G relationship** line in the form the existing profile uses.
   It says which property the profile can supply evidence toward, and states that the
   profile result is never that property's result.

| Profile | Proposed A–G relationship |
|---|---|
| Cumulative authority limits | No A–G property covers admission of an accumulated amount. Relevant evidence for **D — Semantic Authority** (a sequence of permitted calls whose sum is not permitted). Never a D or F result. |
| Cryptographic authority integrity | Prerequisite evidence for the authenticity component of **A — Receipt Integrity**. Never an A result: it does not cover validity periods, replay bounds (A, F), issuer authority (B) or the exact call (C). |
| Agent cyber boundary | Per class. Command and tool substitution is relevant evidence for **E — Execution-Boundary Integrity**. Untrusted instruction promotion is relevant evidence for **B** and **D**. Secret egress, network and artifact admission have no A–G counterpart. Never an E, B or D result. |

5. **Non-transitivity is stated in both directions where both exist.** Where a profile is a
   prerequisite of a property's component (cryptographic integrity and A), the relationship
   is one-directional and is stated as such. The proposal's §1.1 calls I distinct from A–C;
   for A that is not accurate, because a failed authenticity check also prevents A from
   being established. ADR text and profiles must say "prerequisite of A's authenticity
   component", not "independent of A".

## Consequences

- No schema or record can carry a property letter after G, so "A–J" summaries cannot be
  produced from AACP data.
- Every profile document needs its own counterexamples (DRAFT-CLAIMS.md) showing that its
  result and the related property's result can differ.
- The proposal's §1.1 sentence "I vs A–C" is amended by this ADR for A; B and C stay
  two-directional and are illustrated in DRAFT-CLAIMS.md.

## Alternatives considered

- **Keep H/I/J as identifiers.** Rejected: collides with the property namespace and with
  TERMINOLOGY.md profile identity.
- **Declare new properties H–J in a v0.3 specification.** Rejected for this SDD: it would
  change the A–G model that the proposal itself requires to stay unchanged, and it needs
  its own specification process.
