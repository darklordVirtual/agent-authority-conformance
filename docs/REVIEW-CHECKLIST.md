# Cross-project review checklist

Use this checklist for every federation-style AAC run.

## Before the run
- [ ] Maintainer invitation, public verification request or explicit permission recorded.
- [ ] Full subject commit SHA frozen.
- [ ] Exact artifact bytes and hashes frozen.
- [ ] Adapter and procedure revisions frozen.
- [ ] Named claims and explicit non-claims agreed or clearly proposed.
- [ ] Source class and independence level recorded for each artifact.
- [ ] Expected results kept outside verifier input.
- [ ] Mutation permission recorded separately.
- [ ] Private/public review and release rule recorded.

## Mechanical review
- [ ] No path traversal or mutable branch reference.
- [ ] Every required artifact resolves to the expected SHA-256.
- [ ] Adapter does not execute producer code unless the procedure explicitly requires and sandboxes it.
- [ ] Missing/mismatched input produces a non-verdict.
- [ ] Output contains no aggregate score.
- [ ] Output is deterministic where the procedure permits.
- [ ] A rerun has lineage to the earlier run rather than overwriting it.

## Evidence review
- [ ] Resolution is not confused with admission.
- [ ] Producer-authored evidence is labelled as such.
- [ ] Synthetic premises remain synthetic.
- [ ] Completeness/coverage claims have evidence outside caller-controlled booleans.
- [ ] Runtime success is not used as effect evidence.
- [ ] Signature validity is not used as authority/effect evidence without the required additional premises.
- [ ] Partial scope names the untested remainder.
- [ ] NOT_ESTABLISHED names unresolved obligations.

## Maintainer review
- [ ] Factual interpretation sent to producer before publication when required.
- [ ] Corrections are incorporated with provenance.
- [ ] Technical disagreement is retained, not silently normalized away.
- [ ] Review is not described as endorsement.
- [ ] Publication permission satisfies the frozen rule.
- [ ] Public text repeats the claim ceiling and material non-claims.

## Adequacy follow-up
- [ ] Mutation experiment is separately scoped.
- [ ] Positive and inert controls are present.
- [ ] All survivors are retained.
- [ ] Survivors are described as discrimination limits unless stronger evidence supports another classification.
