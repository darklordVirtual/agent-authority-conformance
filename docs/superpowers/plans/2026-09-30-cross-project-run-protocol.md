# Cross-project run protocol (v0.3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `conformance/lab/`, a stdlib-only tool that scopes, freezes, runs, packages, privately shares, publishes and reruns bounded tests (adequacy and verification) against other projects' pinned artifacts, following the principles agreed in aeoess/agent-governance-vocabulary#177.

**Architecture:** Each run lives in a directory `runs/<run_id>/` (gitignored). A lifecycle guard in `STATE.json` and an append-only hash-chained `CONSENT.json` gate every command. Engines (native, corpus-adequacy) report movement per mutant; `kinds/adequacy.py` classifies. The package vendors the lab code and a `rerun.py`, and becomes a private repository in the `R-research-lab` organisation.

**Tech Stack:** Python ≥ 3.12 standard library (`conformance/lab/`), `git` and `gh` CLIs, `unittest`; `jsonschema` only in repository tests.

**Spec:** `docs/superpowers/specs/2026-09-30-cross-project-run-protocol-design.md`

## Global Constraints

- `conformance/lab/` imports only the Python standard library (Python ≥ 3.12).
- The existing `conformance/boundary.py`, `check.py`, `validation.py`, v0.1/v0.2 specs and schemas are not modified.
- Canonical JSON: `json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"`, UTF-8; hashes are SHA-256 hex over file bytes.
- Keys `overall`, `score`, `total`, `aggregate`, `grade` are rejected anywhere in lab documents.
- Exit codes: 0 success / REPRODUCED; 1 completed measurement with survivors / DIVERGED; 2 any `LabError` / NOT_REPRODUCIBLE.
- Organisation: `lab.toml` sets `org = "R-research-lab"`; `share` refuses non-organisation owners.
- `runs/*` is gitignored (unreleased results and quoted third-party material never enter this repository).
- The only network steps are subject fetch (`git clone`) and `gh`/`git push`; tests never contact the network.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Pinned source files with CRLF line endings: anchors must match the exact bytes; the mutated file keeps CRLF (Task 5 test `test_crlf_anchor`).
2. Adapters that print warnings before their JSON line: the projection is the last non-empty stdout line (Task 5 test `test_warning_lines_before_projection`).
3. Case ids containing `/` or spaces: case files are named by index, not id (Task 5 test `test_case_id_with_slash`).
4. Run and package directories whose path contains spaces: all tests run inside a temp dir named `aac lab …` (Task 1 helper).
5. A `publication_approved` event from someone who is not a named approver never counts (Task 2 test `test_non_approver_approval_ignored`).

---

### Task 1: Foundation (errors, canonical JSON, config, test helpers)

**Files:** Create `conformance/lab/__init__.py`, `errors.py`, `canonical.py`, `config.py`, `lab.toml`, `runs/README.md`, `tests/__init__.py`, `tests/lab/__init__.py`, `tests/lab/helpers.py`, `tests/lab/test_canonical.py`; Modify `.gitignore`.

**Produces:** `LabError(exit_code=2)` and subclasses `GateError, ScopeError, PinError, PlanError, EngineError, PackageError, GitHubError`; `canonical.dumps/write_json/read_json/sha256_bytes/sha256_file/sha256_json/find_forbidden_keys/utc_now`; `config.load_config(root) -> {"org", "runs_dir"}`; helpers `NOW`, `LabTest` (temp dir with a space, git identity env, `insteadOf` map from `https://example.invalid/` to a local remotes dir), `make_repo(path, files) -> commit`.

- [ ] Tests: canonical bytes are sorted/indented/newline-terminated; duplicate keys raise `ScopeError`; forbidden keys found at nested paths; config reads `lab.toml`.
- [ ] Implement; run `python -m unittest tests.lab.test_canonical -v` → PASS; commit.

### Task 2: Lifecycle state and consent log

**Files:** Create `conformance/lab/state.py`, `consent.py`, `tests/lab/test_state.py`, `tests/lab/test_consent.py`.

**Produces:** `state.STATES`, `TRANSITIONS`, `new_state(run_dir, now)`, `load_state`, `require(run_dir, *states)`, `save`, `transition(run_dir, to, now, note="", **fields)`; `consent.ACTIONS`, `load`, `add(run_dir, who, action, ref, now)`, `verify_chain`, `has_all(events, people, action)`, `publication_status(events, approvers) -> "approved"|"declined"|"pending"`.

- [ ] Tests: every illegal transition rejected (exhaustive over STATES×STATES); history appended; consent requires https ref and known action; editing any event breaks the chain; `publication_status` pending/approved/declined and later `withdrawn` wins; `test_non_approver_approval_ignored`.
- [ ] Implement; run tests → PASS; commit.

### Task 3: Scope and fault validation, schemas, fixtures

**Files:** Create `conformance/lab/scope.py`, `faults.py`, `schema/lab/{scope,faults,consent,claim-results,row-result}.schema.json`, fixtures `tests/lab/fixtures/{toy-subject,toy-run,toy-receipts,toy-verification-run}/…`, `tests/lab/test_scope.py`, `tests/lab/test_schema_agreement.py`.

**Produces:** `scope.validate_scope(scope, require_pins=False)`, `load_scope(run_dir, require_pins=False)`; `faults.load_fault_set(path)` (requires `name`, `set ∈ {known, held_out}`, `source{author, https ref}`), `load_control(path, polarity)`, `row_mutations(run_dir, scope, row) -> (controls, faults)` (each fault gets `set`, `set_name`), `read_source(path)` (newline-preserving), `apply_mutation(text, mutation)` (anchor exactly once else `PlanError`).

- [ ] Tests: both toy scopes valid; each required field removed → `ScopeError` naming it; aggregate key rejected; INDEPENDENT without statement rejected; adequacy with two subjects rejected; temporal claim without `reference_time` rejected; stdlib and `jsonschema` agree on valid/invalid fixtures.
- [ ] Implement; run → PASS; commit.

### Task 4: Pins

**Files:** Create `conformance/lab/pins.py`, `tests/lab/test_pins.py`.

**Produces:** `fetch(repo, commit, dest)`, `hash_paths(root, paths) -> {posix: sha}`, `verify(root, expected)`, `export(clone, paths, dest)`, `materialize(scope, workdir) -> (trees, licenses)`.

- [ ] Tests: fetch exact commit; one changed byte → `PinError`; missing file → `PinError`; unpinned extra file under declared path → `PinError`; export contains only declared paths; licence text captured.
- [ ] Implement; run → PASS; commit.

### Task 5: Engines (interface + native)

**Files:** Create `conformance/lab/engines/{__init__,base,native}.py`, `tests/lab/test_native.py`.

**Produces:** `Outcome(fault_id, moved, crashed, engine_verdict=None, diff={})`; `Engine.identity()`, `Engine.measure(tree, row, controls, faults) -> {"controls": {...}, "faults": [...], "engine_report": dict|None}`; `get_engine(config)`, `identity_for(scope)`; `NativeEngine(timeout).baseline(tree, row)`, `run_case`.

- [ ] Tests on toy tree: F1/F2 moved, F3 zero, F4 crashed; baseline crash → `EngineError`; `test_crlf_anchor`; `test_warning_lines_before_projection`; `test_case_id_with_slash`.
- [ ] Implement; run → PASS; commit.

### Task 6: Adequacy and verification kinds

**Files:** Create `conformance/lab/kinds/{__init__,adequacy,verification}.py`, `tests/lab/test_kinds.py`.

**Produces:** `adequacy.classify(outcome)`, `row_status(controls)`, `check_expected`, `prepare_tree(run_dir, tree)`, `execute_row(run_dir, scope, tree, row, engine) -> (result, engine_report)`; `verification.execute(run_dir, scope, trees) -> records`, `agreement(run_dir, records)`.

- [ ] Tests: classification table; unkilled positive → `VOID_NO_SCORE`; moved inert → `VOID`; crash counted as `killed_crash`; counts grouped by fault-set name, no cross-set sum; baseline mismatch with subject expectations → `PlanError`; verification: exception → `ERROR` with `verifier_error`; undeclared read → `ERROR`; `NOT_ESTABLISHED` without obligations → `ERROR`; agreement computed after records, never passed to checks.
- [ ] Implement; run → PASS; commit.

### Task 7: Plan, freeze and run (lifecycle + runner + CLI)

**Files:** Create `conformance/lab/plan.py`, `lifecycle.py` (`init`, `pin`, `freeze`), `runner.py` (`execute`, `run`, `has_survivors`), `__main__.py`, `tests/lab/test_lifecycle.py`.

- [ ] Tests: `init` skeleton / template / follow-up (inherits faults, clears pins, links previous plan hash); `pin` refused after `scope_agreed`; `freeze` refused without every agreement party's `scope_agreed` and `run_authorized`; non-unique anchor and unparsable replacement refused; first freeze prints hash and stays `SCOPED`; `--published-ref` before a hash exists refused; changed scope after hash refused; `run` end-to-end on toy writes results and exits 1 (survivor); CLI `status`.
- [ ] Implement; run → PASS; commit.

### Task 8: Package and rerun

**Files:** Create `conformance/lab/report.py`, `package.py`, `rerun.py`; extend `lifecycle.py` (`package`), `__main__.py` (`package`, `rerun`); `tests/lab/test_package_rerun.py`.

- [ ] Tests: package contains REPORT/STATUS/NOTICE/REPRODUCE/MANIFEST/rerun.py/lab/ and workflow; REPORT has independence label and no aggregate words; leak scan refuses token, e-mail and `/Users/…`; `python3 rerun.py` → REPRODUCED (0); tampered result with rewritten manifest → DIVERGED (1); tampered result without manifest → NOT_REPRODUCIBLE (2).
- [ ] Implement; run → PASS; commit.

### Task 9: Share, review, publish, withhold

**Files:** Create `conformance/lab/github.py`, `tests/lab/fake_gh.py`, `tests/lab/test_github_flow.py`; extend `lifecycle.py`, `__main__.py`.

- [ ] Tests with fake `gh`: share refuses user owner; creates PRIVATE repo, pushes, invites with `pull`; review → REVIEWED and REVIEW.md; publish refused while any approver pending or declined; publish pushes status commit and flips to PUBLIC; withhold requires a decline; gh failure leaves state unchanged.
- [ ] Implement; run → PASS; commit.

### Task 10: corpus-adequacy engine and cross-check

**Files:** Create `conformance/lab/engines/corpus_adequacy.py`; extend `runner.py` (cross-check, `.local/` originals), `package.py` (ORIGINAL-TO-DELIVERY); `tests/lab/test_corpus_adequacy.py`.

- [ ] Tests: manifest generation (single implementation file, controls first, `{case}`→`{vector}`); verdict translation (`killed`, crash hows, `survived`, unmapped → `not_measured`); integration on toy subject only when `AAC_CORPUS_ADEQUACY` is set (skipped otherwise).
- [ ] Implement; run → PASS; commit.

### Task 11: Documentation and CI

**Files:** Create `RUN-PROTOCOL-v0.3.md`; Modify `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `.github/workflows/validate-assessments.yml` (Python 3.12 job already runs `unittest discover -s tests`; add `git` identity for fixture commits).

- [ ] Write docs; run full suite `python -m unittest discover -s tests -v` and `python -m conformance.check`; commit.

### Task 12: Scope templates and REMORA reference run

**Files:** Create `templates/scopes/aps-priorseal-verification.json`, `templates/scopes/agentavow-tmd-verification.json`, `scripts/make_remora_v12_run.py`, `tests/lab/test_templates.py`.

- [ ] Templates: pinned full SHAs (APS `948f99b85343bef2c6fa677c8543965caacfc087`, PriorSeal `d749d2691c3e6be139de4020e7b27cdafca2c428`, AgentAvow `4404df2c4176ca5390f1af5a2e63f069a503a01f`), `agreement_ref: null`, draft note; test that they parse and that `freeze` refuses them without consent.
- [ ] Script builds `runs/remora-es-v12-adequacy/` (SELF_RUN, REMORA `c1345b1f9e0f877454bf996b2160d533c5a9b16a`, fault sets converted from Rul1an's public `remora-es-v11-adequacy@9f3851995bbe395e510dde9ce9a03ebb6f1f965a` with attribution, own adapter), then runs `pin`. Freeze/run need consent events recorded by the maintainer.
- [ ] Commit.
