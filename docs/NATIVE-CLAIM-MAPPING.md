# Native claim preservation and AAC mapping

Foreign projects keep ownership of their claim vocabulary. AAC records a native
claim first, then optionally records a relationship to A-G.

Allowed relationships:

- `exact`: same bounded question under the stated procedure.
- `structural`: same shape or binding mechanism, not the same semantic claim.
- `partial`: supports only part of the AAC property.
- `false_analog`: superficially similar but the inference would be invalid.
- `no_mapping`: deliberately kept outside A-G.
- `not_evaluated`: relationship has not been assessed.

Mappings never translate a producer result into AAC PASS/FAIL automatically.
They are crosswalk metadata and must retain the producer's original claim id,
result vocabulary, scope and ceiling.
