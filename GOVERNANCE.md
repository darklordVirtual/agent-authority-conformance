# Governance

## Maintainer

The repository is maintained by `darklordVirtual`. Maintenance is editorial:
the maintainer decides what is merged, not what any implementation is worth.

## Proposing a profile

A profile proposal is a pull request that adds `profiles/<name>/v<n>/` with
the six parts named in [TERMINOLOGY.md](TERMINOLOGY.md#profile-identity) and a
`CLAIM_CEILING.md`. The proposer may be the project whose property the profile
describes. Once merged, that project has no privileged position under the
profile (CHARTER principle 1).

A profile revision is frozen when merged. A fixture added later goes into a
new revision. A fixture found wrong is corrected in a new revision; the old
revision and every record written under it stay as published.

## Recording a run

A run is a pull request that adds one record under `runs/`. The record binds
the profile revision, fixture digests, implementation revision, evaluator
revision, environment, level and result, and repeats the claim ceiling. The
maintainer checks the binding, not the outcome. A `CONTRADICTED` record is
merged on the same terms as an `ESTABLISHED` one, and the implementation it
describes may answer with a record of its own, never by editing the first.

## Review policy

Producer review of a record is seven days. An unresolved disagreement is
published as a disagreement, next to the record, not withheld.

## Relation to external venues

Profiles and records are written so they can be contributed to a neutral
conformance venue such as the LF Decentralized Trust Agent Authority
Conformance lab, which keeps results separate per contributed specification.
Contribution is the maintainer's decision; it changes nothing about the
profile's status here.
