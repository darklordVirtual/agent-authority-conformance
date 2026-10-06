# RFC189 observed-effect OE-08 source adapter

This adapter resolves one public candidate fixture only:

`RFC189-OE-08-NE-SELF-VANTAGE-CLAIMING-INDEPENDENCE`

It does not execute upstream code. Resolution proves only that the checked-out
subject contains the exact bytes pinned in `adapter.json`.

The AACP-owned inference rule that uses the semantic discriminator is separate:

- profile: `profiles/AACP-OBSERVED-EFFECT-VANTAGE-1.md`
- procedure: `conformance/observed_effect_vantage.py`
- normalized case: `interop/fixtures/rfc189-oe-08-self-vantage.json`

That separation prevents a producer-authored expected answer from becoming
checker input.

## Resolve the upstream bytes

```sh
git clone --no-checkout https://github.com/astrogilda/ws4-secure-design-agentic-systems.git ../rfc189-subject
git -C ../rfc189-subject checkout --detach 7deaf432394e8a332423a70b5e699d20e990b137
python -m scripts.run_federation_adapter \
  --manifest adapters/rfc189-observed-effect-oe08-vantage-v1/adapter.json \
  --subject-root ../rfc189-subject \
  --record-dir ../rfc189-oe08-resolution \
  --runner YOUR_ACTUAL_OPERATOR_ID \
  --fixture-author astrogilda \
  --classification REPRODUCTION
```

## Run the independent AACP rule

```sh
python -m conformance.observed_effect_vantage \
  interop/fixtures/rfc189-oe-08-self-vantage.json
```

The second command evaluates AACP's normalized facts. It does not import or run
the upstream verifier and does not import a target implementation such as
REMORA.

A later REMORA, Heimel or other implementation run should adapt that
implementation's native result to the frozen profile contract and record the
implementation revision, adapter/procedure revision and operator provenance
separately.
