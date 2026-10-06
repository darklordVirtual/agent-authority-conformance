# AACP-OBSERVED-EFFECT-VANTAGE-1

**Status:** draft bounded profile  
**Purpose:** discriminate self-vantage from independently established observation vantage  
**Method:** Bounded Claim Reproduction (BCR)  
**A-G relationship:** partial prerequisite evidence for **G — Effect Verification**; never a G result by itself

## Claim

For a property that requires an independent observation of an external effect:

> A record produced from the observed party's own vantage does not establish
> independent observation merely because the record declares itself independent.

The profile is deliberately asymmetric. It can refuse an independence claim
from self-vantage. It does not infer that an observed effect is false.

## Public source anchor

The first discriminator is derived from the public candidate fixture:

- repository: `astrogilda/ws4-secure-design-agentic-systems`
- revision: `7deaf432394e8a332423a70b5e699d20e990b137`
- path: `conformance/RFC-189/observed-effect/cases/RFC189-OE-08-NE-SELF-VANTAGE-CLAIMING-INDEPENDENCE.json`
- raw SHA-256: `5a1aa5bcfdc7afaf6af9ae830f5a09c84234cf07c95888a155d72332dd4c8a6b`
- Git blob: `1a3f468173446deb3c9001459a86cf0ffd303b72`
- upstream case status at that revision: `candidate`
- document revision named by the case: `84604125869469926968acdf433501f87d1d1665`

AACP preserves the upstream native expectation separately from its own
normalized input. The upstream fixture is a source anchor, not an AACP
certification target and not evidence of CoSAI or RFC endorsement.

## Input contract

The verifier consumes only these normalized facts:

- `observer_id`
- `observed_party`
- `control_domain`
- `observed_control_domain`
- `can_observed_party_forge`
- `can_observed_party_suppress`
- `declared_independence`

Trust in an external control domain is **not** accepted from the record.
`trusted_control_domains` is runner-owned trust material supplied separately.

Expected results are outside checker input.

## Procedure

`conformance.observed_effect_vantage.evaluate_observation_vantage` applies the
following bounded rules:

1. If `observer_id == observed_party`, return `NOT_ESTABLISHED` with unmet
   obligation `observation_vantage`, regardless of
   `declared_independence` or textual control-domain labels.
2. If the observed party can forge or suppress the observation, independence is
   `NOT_ESTABLISHED`.
3. Shared control domain is not independent.
4. A distinct control domain establishes independence only when that domain is
   in verifier-owned trust material **and** explicit forge/suppress facts are
   both false.
5. Missing evidence stays `NOT_ESTABLISHED`; malformed typed input is
   `INVALID_INPUT`, a non-verdict.

The reason `authoritative-vantage-not-independent` is retained for the OE-08
discriminator so external runs can compare semantics without treating reason
wording as a global AACP vocabulary.

## Required discriminators

A conforming second implementation should exercise at least:

- OE-08 self-vantage with `declared_independence=true` -> `NOT_ESTABLISHED`;
- self-vantage with a nominally different/trusted domain label -> still
  `NOT_ESTABLISHED`;
- external observer, distinct trusted control domain, explicit no-forge and
  no-suppress -> `ESTABLISHED`;
- external observer in the same control domain -> `NOT_ESTABLISHED`;
- external observer in an untrusted domain -> `NOT_ESTABLISHED`;
- forge or suppress capability -> `NOT_ESTABLISHED`;
- malformed boolean input -> `INVALID_INPUT`.

## Local reproduction

```sh
python -m conformance.observed_effect_vantage \
  interop/fixtures/rfc189-oe-08-self-vantage.json
```

Expected AACP output:

```json
{"reason":"authoritative-vantage-not-independent","result":"NOT_ESTABLISHED","unmet_obligation":"observation_vantage"}
```

The committed unit tests also include positive and adversarial controls:

```sh
python -m unittest tests.test_observed_effect_vantage -v
```

## Claim ceiling

A matching result establishes only that the implementation reproduces this
bounded observation-vantage rule under the frozen profile.

It does **not** establish:

- truth or falsity of the observed effect;
- observation coverage completeness;
- source authenticity merely from a key or digest;
- causation;
- authorization;
- global non-bypassability;
- AACP property G as a whole;
- RFC-189 conformance;
- CoSAI endorsement;
- production certification.

A runtime or verifier that matches this profile should retain its native result
and provenance. AACP records the reproduction separately; it does not rename a
foreign project's result or convert it into aggregate A-G credit.
