# Scope templates

Drafts for runs against external projects. They are **not agreed** and cannot be
frozen: `freeze` requires an `agreement_ref` and `scope_agreed` plus
`run_authorized` from every agreement party. Start a run from a template with

```sh
python -m conformance.lab init <run_id> --template templates/scopes/<file>.json
```

then settle claims, `reads_fields`, the verifier and licence handling with the
named maintainers in a public issue before recording anything. Each template's
`draft_note` lists what is still open.
