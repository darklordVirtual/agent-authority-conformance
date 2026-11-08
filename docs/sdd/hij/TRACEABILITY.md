# Traceability: requirements to planned tests

**Status:** every row is PLANNED. Stage 0 adds no test. Paths follow ADR-0002's proposed layout and are
provisional until it is decided; a renamed path keeps its row. A test is written, and seen to fail, before
the code that makes it pass, and is never edited to match an implementation's output.

Vector paths abbreviate `profiles/<identifier>/v1/` as `.../v1/`. Agent cyber test files assume ADR-0004
option 2 (one file per class). Each JX row is **proposed and not independently implemented**; its distinct parent-vector mapping, seeded mutant and observation conditions are defined in
`reviews/STAGE-0-CYBER-TEST-EXPANSION.md`. No row implies test coverage or Gate 0/4 completion.

| Requirement | Source | Planned test | Vectors | Stage | Status |
|---|---|---|---|---|---|
| AC-01 legacy compatibility | §8 | `tests/profiles/test_legacy_regression.py::test_legacy_specs_and_schemas_byte_identical, ::test_check_output_matches_baseline_snapshot` | baseline snapshot | 1 | PLANNED |
| AC-02 schema discipline | §8, ADR-0003 | `tests/profiles/test_schema_contract.py::test_shape_refusals (SA-2.1–2.7)` | schema fixtures | 1 | PLANNED |
| AC-03 fail-closed inference | §8, ADR-0003 | `tests/profiles/test_schema_contract.py::test_combination_table (SA-3); each profile ::test_missing_fact_is_not_established` | schema + profile fixtures | 1–4 | PLANNED |
| AC-04 negative discrimination | §8 | `each profile ::test_every_negative_family_detected, ::test_mutants_reported_with_survivors` | NEG + mutation sets | 2–4 | PLANNED |
| AC-05 H correctness | §8 | `tests/profiles/test_cumulative_authority_limits.py::test_non_atomic_ledger_detected, ::test_single_approver_cannot_cross, ::test_unknown_stays_charged` | H-NEG-01, -06, -03 | 2 | PLANNED |
| AC-06 I correctness | §8 | `tests/profiles/test_cryptographic_authority_integrity.py::test_trusted_raw_bytes_verify, ::test_wrong_key_domain_preimage_refused, ::test_in_package_key_not_trust` | I-POS, I-NEG-02/03/06/09 | 3 | PLANNED |
| AC-07 J correctness | §8, ADR-0004 | `each class ::test_class_evaluated_or_nonverdict, ::test_canary_never_leaves_test_sink` | J-NEG per class | 4 | PLANNED |
| AC-08 no transitive credit | §1.1, §8, ADR-0001 | `tests/profiles/test_non_transitivity.py::test_counterexample_pairs (one per row of DRAFT-CLAIMS counterexamples)` | paired fixtures | 2–4 | PLANNED |
| AC-09 non-aggregation | §8, ADR-0003 | `tests/profiles/test_schema_contract.py::test_aggregate_keys_refused_at_depth; tests/profiles/test_outputs.py::test_cli_and_docs_print_no_combined_result` | schema fixtures | 1, 5 | PLANNED |
| AC-10 reproducibility | §8, ADR-0003 | `tests/profiles/test_rerun.py::test_divergence_on_every_field, ::test_tampered_package_not_reproduced` | package fixtures | 5 | PLANNED |
| AC-11 safety and provenance | §8, §5 | `tests/profiles/test_safety.py::test_fixtures_inert, ::test_no_network_in_default_suite, ::test_ai_disclosure_required` | — | 1–5 | PLANNED |
| AC-12 CI and review | §8 | `workflow diff review; review record per stage in docs/sdd/hij/reviews/` | — | all | PLANNED |
| ADR-0001 no property letters | ADR-0001 | `tests/profiles/test_schema_contract.py::test_letter_identifiers_refused` | SA-2.3 | 1 | PLANNED |
| ADR-0003 level consistency | ADR-0003 | `tests/profiles/test_schema_contract.py::test_level_inconsistent_with_roles_refused` | SA-4.3 | 1 | PLANNED |
| H1 bound resource and accounting | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_h1_*` | H-NEG-05 | 2 | PLANNED |
| H2 atomic shared accounting | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_h2_*` | H-NEG-01, H-NEG-11 | 2 | PLANNED |
| H3 fail closed | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_h3_*` | H-NEG-04 | 2 | PLANNED |
| H4 unknown effect | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_h4_*` | H-NEG-03 | 2 | PLANNED |
| H5 replay and lifecycle | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_h5_*` | H-NEG-02, H-NEG-10 | 2 | PLANNED |
| H6 conditional escalation | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_h6_*` | H-NEG-06 to -09 | 2 | PLANNED |
| H7 observation | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_h7_*` | H-NEG-12 | 2 | PLANNED |
| H-NEG-01 concurrent overbook | §3; DRAFT-CLAIMS H-F1 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_01` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-01 | 2 | PLANNED |
| H-NEG-02 replayed operation | §3; DRAFT-CLAIMS H-F2 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_02` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-02 | 2 | PLANNED |
| H-NEG-03 restart while unknown | §3; DRAFT-CLAIMS H-F3 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_03` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-03 | 2 | PLANNED |
| H-NEG-04 missing policy or ledger | §3; DRAFT-CLAIMS H-F4 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_04` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-04 | 2 | PLANNED |
| H-NEG-05 unit or scale mismatch | §3; DRAFT-CLAIMS H-F5 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_05` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-05 | 2 | PLANNED |
| H-NEG-06 threshold crossing with one approver | §3; DRAFT-CLAIMS H-F6 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_06` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-06 | 2 | PLANNED |
| H-NEG-07 same identity twice | §3; DRAFT-CLAIMS H-F7 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_07` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-07 | 2 | PLANNED |
| H-NEG-08 approval revoked before crossing | §3; DRAFT-CLAIMS H-F8 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_08` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-08 | 2 | PLANNED |
| H-NEG-09 total changed between approval and dispatch | §3; DRAFT-CLAIMS H-F9 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_09` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-09 | 2 | PLANNED |
| H-NEG-10 policy replaced in window | §3; DRAFT-CLAIMS H-F10 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_10` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-10 | 2 | PLANNED |
| H-NEG-11 cross-tenant budget bleed | §3; DRAFT-CLAIMS H-F11 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_11` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-11 | 2 | PLANNED |
| H-NEG-12 over-limit sequence labelled safe | §3; DRAFT-CLAIMS H-F12 | `tests/profiles/test_cumulative_authority_limits.py::test_neg_12` | profiles/AACP-CUMULATIVE-AUTHORITY-LIMITS/v1/negative/H-NEG-12 | 2 | PLANNED |
| H-POS-01 at limit (inclusive) | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_pos_01` | .../v1/positive/H-POS-01 | 2 | PLANNED |
| H-POS-02 one unit below | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_pos_02` | .../v1/positive/H-POS-02 | 2 | PLANNED |
| H-POS-03 one unit above | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_pos_03` | .../v1/positive/H-POS-03 | 2 | PLANNED |
| H-POS-04 hard limit | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_pos_04` | .../v1/positive/H-POS-04 | 2 | PLANNED |
| H-POS-05 permitted two-approver crossing | §3 | `tests/profiles/test_cumulative_authority_limits.py::test_pos_05` | .../v1/positive/H-POS-05 | 2 | PLANNED |
| H-DISC-01 critical discriminator (steps 1, 2a, 2b, 3) | §3; DRAFT-CLAIMS | `tests/profiles/test_cumulative_authority_limits.py::test_critical_discriminator` | .../v1/mutation/H-DISC-01 | 2 | PLANNED |
| I1 explicit algorithm suite | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_i1_*` | I-NEG-08, I-NEG-11 | 3 | PLANNED |
| I2 exact signing preimage | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_i2_*` | I-NEG-06, I-NEG-10 | 3 | PLANNED |
| I3 authenticated trust root | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_i3_*` | I-NEG-09, I-NEG-12 | 3 | PLANNED |
| I4 key separation and lifecycle | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_i4_*` | I-NEG-02, -03, -04, -07 | 3 | PLANNED |
| I5 context integrity | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_i5_*` | I-NEG-05 | 3 | PLANNED |
| I6 independent verification | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_i6_*` | RFC 8032 §7.1 vectors; cross-implementation vectors | 3 | PLANNED |
| I-NEG-01 one-bit change | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_01` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-01 | 3 | PLANNED |
| I-NEG-02 wrong key | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_02` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-02 | 3 | PLANNED |
| I-NEG-03 wrong signature domain | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_03` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-03 | 3 | PLANNED |
| I-NEG-04 key usage or context mismatch | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_04` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-04 | 3 | PLANNED |
| I-NEG-05 changed tenant, tool or policy digest | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_05` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-05 | 3 | PLANNED |
| I-NEG-06 ambiguous framing | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_06` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-06 | 3 | PLANNED |
| I-NEG-07 stale or revoked key | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_07` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-07 | 3 | PLANNED |
| I-NEG-08 invalid or unknown algorithm | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_08` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-08 | 3 | PLANNED |
| I-NEG-09 untrusted in-package key | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_09` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-09 | 3 | PLANNED |
| I-NEG-10 duplicate keys or serialization mismatch | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_10` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-10 | 3 | PLANNED |
| I-NEG-11 digest-only pseudo-attestation | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_11` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-11 | 3 | PLANNED |
| I-NEG-12 MAC claimed verifiable without secret | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_neg_12` | profiles/AACP-CRYPTOGRAPHIC-AUTHORITY-INTEGRITY/v1/negative/I-NEG-12 | 3 | PLANNED |
| I-NV-01 missing trust root or reference time is a non-verdict | §4 | `tests/profiles/test_cryptographic_authority_integrity.py::test_missing_trust_material_nonverdict` | .../v1/negative/I-NV-01 | 3 | PLANNED |
| J1 instruction promotion | §5; ADR-0004 | `tests/profiles/test_agent_cyber_instruction_promotion.py::test_negatives, ::test_legitimate_workflow_still_succeeds` | J-NEG-01, J-NEG-02 | 4 | PLANNED |
| J2 secret egress | §5; ADR-0004 | `tests/profiles/test_agent_cyber_secret_egress.py::test_negatives, ::test_legitimate_workflow_still_succeeds` | J-NEG-03, J-NEG-10 | 4 | PLANNED |
| J3 network | §5; ADR-0004 | `tests/profiles/test_agent_cyber_network.py::test_negatives, ::test_legitimate_workflow_still_succeeds` | J-NEG-04, J-NEG-05, J-NEG-09 | 4 | PLANNED |
| J4 tool substitution | §5; ADR-0004 | `tests/profiles/test_agent_cyber_tool_substitution.py::test_negatives, ::test_legitimate_workflow_still_succeeds` | J-NEG-06 | 4 | PLANNED |
| J5 artifact admission | §5; ADR-0004 | `tests/profiles/test_agent_cyber_artifact_admission.py::test_negatives, ::test_legitimate_workflow_still_succeeds` | J-NEG-07 | 4 | PLANNED |
| J6 observation | §5; ADR-0004 | `tests/profiles/test_agent_cyber_observation.py::test_negatives, ::test_legitimate_workflow_still_succeeds` | J-NEG-08, J-NEG-11, J-NEG-12 | 4 | PLANNED |
| J-OBS observation prerequisite (blind detector) | §5 J6; ADR-0004 | `each class ::test_established_requires_detected_positive_control` | seeded positive controls | 4 | PLANNED |
| J-SAFE no egress beyond test sink; fake canary format | §5 safety | `tests/profiles/test_safety.py::test_canary_format_and_sink` | — | 4 | PLANNED |
| JX-01 forged role delimiters | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_instruction_promotion.py::test_jx01_forged_role` | proposed JX-01; parent J-NEG-01 | 4 | PLANNED |
| JX-02 forged approval receipt | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_instruction_promotion.py::test_jx02_forged_approval` | proposed JX-02; parent J-NEG-01 | 4 | PLANNED |
| JX-03 resumed persistent taint | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_instruction_promotion.py::test_jx03_persistent_taint` | proposed JX-03; parent J-NEG-02 | 4 | PLANNED |
| JX-04 protected canary transform and attacker-lookalike negative | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_secret_egress.py::test_jx04_provenance_and_transform` | proposed JX-04; parent J-NEG-03 | 4 | PLANNED |
| JX-05 cross-tenant protected-source read | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_secret_egress.py::test_jx05_tenant_source_and_context` | proposed JX-05; parent J-NEG-10 | 4 | PLANNED |
| JX-06 redirect final network peer | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_network.py::test_jx06_redirect_final_peer` | proposed JX-06; parent J-NEG-05, J-NEG-09 | 4 | PLANNED |
| JX-07 DNS authorization/connect change | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_network.py::test_jx07_dns_rebinding` | proposed JX-07; parent J-NEG-04 | 4 | PLANNED |
| JX-08 policy/connector parser drift | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_network.py::test_jx08_parser_peer` | proposed JX-08; parent J-NEG-04, J-NEG-09 | 4 | PLANNED |
| JX-09 effective executable and arguments | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_tool_substitution.py::test_jx09_executable_arguments` | proposed JX-09; parent J-NEG-06 | 4 | PLANNED |
| JX-10 immutable callable identity | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_tool_substitution.py::test_jx10_callable_identity` | proposed JX-10; parent J-NEG-06 | 4 | PLANNED |
| JX-11 pinned bytes versus loaded bytes | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_artifact_admission.py::test_jx11_loaded_bytes` | proposed JX-11; parent J-NEG-07 | 4 | PLANNED |
| JX-12 verify/use artifact replacement | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_artifact_admission.py::test_jx12_execution_time_identity` | proposed JX-12; parent J-NEG-07 | 4 | PLANNED |
| JX-13 blind interval versus admitted contradiction precedence | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_observation.py::test_jx13_blind_interval_precedence` | proposed JX-13; parent J-NEG-08, J-NEG-11 | 4 | PLANNED |
| JX-14 boundary effect takes precedence over self-report | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_observation.py::test_jx14_effect_precedence` | proposed JX-14; parent J-NEG-09, J-NEG-12 | 4 | PLANNED |
| JX-15 matched runner control detection | Stage 0 cyber expansion §Evidence and §Parent-vector mapping | `tests/profiles/test_agent_cyber_observation.py::test_jx15_control_match` | proposed JX-15; parent J-NEG-08, J-NEG-12 | 4 | PLANNED |
