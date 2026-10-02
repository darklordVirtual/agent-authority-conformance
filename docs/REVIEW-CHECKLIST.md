# Cross-project review checklist

## Before the run
- [ ] Subject repository and full commit SHA frozen.
- [ ] Artifact bytes and SHA-256 values frozen.
- [ ] Adapter and procedure revisions frozen.
- [ ] Native claims and explicit non-claims recorded.
- [ ] AAC mapping is absent or explicitly classified.
- [ ] Producer, fixture author, verifier implementation and runner are separate fields.
- [ ] Independence and blinded/non-blinded state recorded.
- [ ] Expected results remain outside verifier input.
- [ ] Review/publication policy is frozen before evaluative execution.

## Mechanical review
- [ ] No mutable branch reference or path traversal.
- [ ] Required artifacts resolve to expected hashes.
- [ ] Producer code is not executed unless explicitly scoped.
- [ ] Missing/mismatched input produces a non-verdict.
- [ ] Output has no aggregate score.
- [ ] Reruns carry lineage rather than overwrite history.

## Evidence review
- [ ] Resolution is not confused with admission.
- [ ] Producer-authored evidence is labelled.
- [ ] Synthetic premises remain synthetic.
- [ ] Completeness claims have evidence beyond caller-controlled booleans.
- [ ] Runtime success is not effect evidence.
- [ ] Signature validity is not treated as semantic authority or effect evidence.
- [ ] Partial scope names the untested remainder.
- [ ] NOT_ESTABLISHED names unresolved obligations.

## Review and publication
- [ ] Factual interpretation is sent to producer when the frozen policy requires it.
- [ ] Corrections retain provenance.
- [ ] Technical disagreement is retained.
- [ ] "Reviewed" is never described as "endorsed".
- [ ] Publication follows the frozen mode/window.
- [ ] Public text repeats claim ceiling and material non-claims.

## Adequacy follow-up
- [ ] Mutation experiment is separately scoped.
- [ ] Positive and inert controls are present.
- [ ] All survivors are retained.
