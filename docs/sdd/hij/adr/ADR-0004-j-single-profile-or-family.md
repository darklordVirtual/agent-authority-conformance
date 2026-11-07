# ADR-0004: Agent cyber boundary as a family of independent class profiles

**Status:** ACCEPTED by maintainer for this design decision (2026-11-07), option 2. This records a design choice, **not** Gate 0 closure, profile publication or test implementation.
**Addresses:** adversarial review B-05; proposal §5, §9 (risk of an unfalsifiable umbrella); AC-07, AC-09

## Context

The proposal defines J as one profile with six mandatory classes (J1–J6), reported
separately, where "a J claim cannot silently ignore a reachable class". That leaves two
readings, and neither is satisfactory:

- **Umbrella reading.** J is established only if every reachable class is. That is an
  aggregate verdict over six different claims, which CHARTER principle 6 and AC-09 exclude
  in spirit, and it makes a J result hard to falsify: it fails for many unrelated reasons.
- **Per-class reading.** Each class has its own claim, failure conditions, vectors and
  ceiling. That is six profiles under one name, and the name invites "J PASS" in prose.

J6 (observation and recovery) is also different in kind. It is the prerequisite that makes
an absence of detections meaningful for J1–J5, much as `AACP-OBSERVED-EFFECT-VANTAGE-1`
is prerequisite evidence for G.

## Options

| Option | Description | Assessment |
|---|---|---|
| 1 | One profile, six mandatory classes (as proposed) | Umbrella risk; unclear result semantics |
| 2 | Six independent profiles, `AACP-AGENT-CYBER-<CLASS>-1`; "agent cyber boundary" is an index category with no result | Each claim falsifiable on its own; no umbrella result can exist |
| 3 | Option 2 plus an inventory profile asserting the declared attack surface is complete | Completeness of an inventory has no practical failure condition; not falsifiable as stated |

## Decision (maintainer accepted, 2026-11-07)

**Option 2 is selected:** six individually scoped profiles, five attack-boundary classes (J1–J5) and one observation-prerequisite profile (J6). There is no family-level result or aggregate security claim. This disposition resolves Stage 0 adversarial finding B-05 only; other blocking items remain subject to their own decisions.

The maintainer also explicitly waived a **separate third-party reviewer as a Gate 0 prerequisite** for this SDD. This is a documented Stage 0 process exception, not an assertion that the AI-drafted review was independently performed. Existing evidence, test-first, reproducibility and implementation-neutrality requirements are unchanged.

The decision has two rules:

1. **Five class profiles** for J1–J5 (instruction promotion, secret egress, network and SSRF,
   command and tool substitution, artifact admission). Each states its attacker capability,
   asset set and observation interval, and gets its own vectors and ceiling.
2. **Observation as a prerequisite profile** for J6. A class profile can be `ESTABLISHED` only
   when, in the same run and interval, the observation prerequisite holds: a seeded positive
   control (a planted canary egress, a planted forbidden request) was detected by the named
   sources. Without it, an **absence-of-effect resistance claim** is `NOT_ESTABLISHED`, because a blind detector cannot establish absence (proposal J6). A forbidden effect independently established by admissible boundary evidence remains `CONTRADICTED` for its observed scope; an observation gap cannot erase that evidence (see PR #26 JX-13/JX-14).

Reachability is part of each class profile's scope declaration. A class declared unreachable
needs evidence for that (`NOT_APPLICABLE` in ADR-0003), never silence. No artifact, CLI or
summary may print a combined result for the family.

## Consequences

- Six profile documents and vector sets instead of one; more review, but each review is
  bounded.
- Stage 4 is split into one sub-stage per class, each with its own gate.
- The proposal's `J-NEG-*` vectors map to classes in TRACEABILITY.md.

## Rejected alternative

Option 1 (one umbrella result) was not selected. If revisited, it requires a new documented ADR decision; it is not an implicit fallback.
