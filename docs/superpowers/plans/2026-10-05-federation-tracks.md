# Federation Tracks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optional self-service (S) and stricter manual (M) tracks for cross-project runs, exposed through `aacp`, with map-record export.

**Architecture:** The v0.3 lab (`conformance/lab/`, stdlib only, vendored into packages) gains a producer-owned offer reader, track-aware gates, admission, conditional consent, per-claim independence, run capture and a runner self-test. `aacp` (PyYAML/jsonschema allowed) wraps the lab and adds `next` and `export map`.

**Tech Stack:** Python ≥ 3.12, stdlib `unittest`, local file-URL git repositories (`tests/lab/helpers.py`), jsonschema and PyYAML only outside the lab.

**Spec:** `docs/superpowers/specs/2026-10-05-federation-tracks-design.md`

## Global Constraints

- Lab code stays standard-library only (it is vendored into every package).
- No `track` in `SCOPE.json` means `manual`; existing fixtures, templates and `runs/remora-es-v12-adequacy` must validate unchanged.
- Forbidden keys anywhere: `overall`, `score`, `total`, `aggregate`, `grade`.
- S allows only `kind: verification`; `executes_producer_code` is the constant `false`.
- Offer `publication.mode` ∈ {`PUBLIC_IMMEDIATE`, `PUBLIC_AFTER_REVIEW`}; the latter needs `review_window_days` ≥ 1; `unresolved_disagreement` ∈ {`PUBLISH_WITH_DISAGREEMENT`, `HOLD`}.
- Admission decisions ∈ {`ADMITTED`, `NOT_ADMITTED`, `UNKNOWN`}; anything but `ADMITTED` → `execution: "NOT_ADMITTED"`, `result: null`, `verifier_error.code: "not_admitted"`.
- `drafted_by` is `"human"` or matches `^agent:[A-Za-z0-9._-]+$`.
- Exporter never writes `owner_confirmation`, never opens a PR, never emits results for a run that is not `PUBLISHED`.
- No absolute local path enters a package (existing leak scan).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Offers file with two entries sharing one `offer_id` → refuse as ambiguous (Task 5 test `test_duplicate_offer_id_refused`).
2. Producer's default branch is not `main` → tip check follows the remote HEAD (Task 5 test `test_tip_follows_default_branch`).
3. `PUBLIC_AFTER_REVIEW` publish when `now` is before the share time (clock skew) → refuse, never negative elapsed time (Task 6 test `test_window_with_clock_before_share_refused`).
4. CLI `--condition` text containing `=` or `,` → only the first `=` splits claims from text (Task 2 test `test_condition_parsing_keeps_text`).
5. Export of an old run without `runner_authored` or per-claim independence → defaults, no crash (Task 8 test `test_export_old_scope_defaults`).

---

### Task 1: Merge main and package the lab

**Files:**
- Merge: `origin/main` (resolve `.gitignore`, `CHANGELOG.md`, `README.md` by keeping both sides)
- Modify: `pyproject.toml` (packages), `conformance/lab/config.py`
- Test: `tests/lab/test_config.py`

**Interfaces:**
- Produces: `load_config(root: Path | None = None) -> dict` — looks for `lab.toml` in `Path.cwd()` first, then `REPO_ROOT`; `runs_dir` is relative to the directory where `lab.toml` was found (or `cwd` if none).

- [ ] **Step 1:** `git merge origin/main`; resolve the three conflicts keeping both texts (CHANGELOG: main's entries above ours under one heading; README: keep main's AACP intro and our pilot guide section; .gitignore: union).
- [ ] **Step 2:** Create a venv in the scratchpad, `pip install -r requirements-dev.txt`, run `python -m unittest discover -s tests` and `python -m conformance.check`. Expected: all pass.
- [ ] **Step 3: Failing test** `tests/lab/test_config.py`:

```python
import os, tempfile, unittest
from pathlib import Path
from conformance.lab.config import load_config

class ConfigTest(unittest.TestCase):
    def test_cwd_lab_toml_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "lab.toml").write_text('org = "x-org"\nruns_dir = "r"\n', encoding="utf-8")
            old = os.getcwd(); os.chdir(tmp)
            try:
                cfg = load_config()
            finally:
                os.chdir(old)
            self.assertEqual(cfg["org"], "x-org")
            self.assertEqual(cfg["runs_dir"].resolve(), (Path(tmp) / "r").resolve())

    def test_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp))
            self.assertEqual(cfg["runs_dir"], Path(tmp) / "runs")
```

- [ ] **Step 4:** Implement: `load_config(root=None)`: if `root` given use it; else `cwd` if `cwd/lab.toml` exists else `REPO_ROOT`.
- [ ] **Step 5:** `pyproject.toml`: `packages = ["aacp", "aacp.schemas", "conformance", "conformance.lab", "conformance.lab.kinds", "conformance.lab.engines"]`; `pip install .` in the venv and `aacp --help` works.
- [ ] **Step 6:** Full suite passes; commit `merge main; package the lab with aacp`.

### Task 2: Consent provenance, conditions, admission and review_ack events

**Files:**
- Modify: `conformance/lab/consent.py`, `conformance/lab/__main__.py`, `schema/lab/consent.schema.json`
- Test: `tests/lab/test_consent.py` (extend)

**Interfaces:**
- Produces: `consent.ACTIONS` adds `"admission"`, `"review_ack"`.
- `consent.add(run_dir, who, action, ref, now, *, drafted_by="human", ai_assisted=False, recorded_by=None, conditions=None, **context)`; `drafted_by`/`ai_assisted` always stored; `recorded_by` and `conditions` only when given. `conditions` only allowed for `scope_agreed`: list of `{"text": str, "claims": [str, ...]}` nonempty.
- `consent.parse_condition(text: str) -> dict` — `"a,b=text with = and , kept"` → `{"claims": ["a","b"], "text": "text with = and , kept"}`; raises `GateError` without `=` or with empty side.
- `consent.admissions(events) -> dict[str, dict]` — latest admission event per input id.
- `consent.conditions(events) -> list[dict]` — every condition with `who`, in order.
- CLI: `consent ... [--condition C]... [--drafted-by D] [--ai-assisted] [--recorded-by H]`; new subcommand `admit RUN --input ID --decision D --rationale TEXT --who H --ref URL [--drafted-by D] [--ai-assisted]`.

- [ ] **Step 1: Failing tests** (append to `tests/lab/test_consent.py`, using `prepare_run`):

```python
class ProvenanceTest(LabTest):
    def setUp(self):
        super().setUp(); self.run = prepare_run(self)

    def test_defaults_and_agent_draft_are_hash_chained(self):
        e = consent.add(self.run, "tester", "scope_agreed", AGREE_REF, NOW)
        self.assertEqual((e["drafted_by"], e["ai_assisted"]), ("human", False))
        e = consent.add(self.run, "tester", "run_authorized", AGREE_REF, NOW, drafted_by="agent:claude", ai_assisted=True)
        self.assertEqual(e["drafted_by"], "agent:claude")
        self.assertEqual(len(consent.load(self.run)), 2)

    def test_bad_drafted_by_refused(self):
        with self.assertRaises(GateError):
            consent.add(self.run, "tester", "scope_agreed", AGREE_REF, NOW, drafted_by="robot")

    def test_old_events_without_fields_still_verify(self):
        from conformance.lab.canonical import write_json
        ev = {"at": NOW, "who": "tester", "action": "scope_agreed", "ref": AGREE_REF, "prev_sha256": consent.GENESIS}
        write_json(self.run / consent.FILE, {"events": [ev]})
        st = read_json(self.run / "STATE.json"); st.pop("consent_head", None); write_json(self.run / "STATE.json", st)
        self.assertEqual(len(consent.load(self.run)), 1)

    def test_conditions_only_on_scope_agreed(self):
        cond = [{"text": "test keys only", "claims": ["exact_call"]}]
        e = consent.add(self.run, "tester", "scope_agreed", AGREE_REF, NOW, conditions=cond)
        self.assertEqual(e["conditions"], cond)
        with self.assertRaises(GateError):
            consent.add(self.run, "tester", "run_authorized", AGREE_REF, NOW, conditions=cond)
        with self.assertRaises(GateError):
            consent.add(self.run, "tester", "scope_agreed", AGREE_REF, NOW, conditions=[{"text": "x", "claims": []}])

    def test_condition_parsing_keeps_text(self):
        self.assertEqual(consent.parse_condition("a,b=keys = test, only"),
                         {"claims": ["a", "b"], "text": "keys = test, only"})
        for bad in ("no equals", "=text", "a="):
            with self.assertRaises(GateError):
                consent.parse_condition(bad)

    def test_admission_latest_wins(self):
        consent.add(self.run, "tester", "admission", AGREE_REF, NOW, input="within", decision="UNKNOWN", rationale="r")
        consent.add(self.run, "tester", "admission", AGREE_REF, NOW, input="within", decision="ADMITTED", rationale="r2")
        self.assertEqual(consent.admissions(consent.load(self.run))["within"]["decision"], "ADMITTED")
        with self.assertRaises(GateError):
            consent.add(self.run, "tester", "admission", AGREE_REF, NOW, input="within", decision="MAYBE", rationale="r")
        with self.assertRaises(GateError):
            consent.add(self.run, "tester", "admission", AGREE_REF, NOW, input="within", decision="ADMITTED", rationale="")
```

- [ ] **Step 2:** Run `python -m unittest tests.lab.test_consent -v` → new tests fail.
- [ ] **Step 3:** Implement in `consent.py`: validation of `drafted_by` (regex), `conditions` (only for `scope_agreed`, nonempty list of dicts with nonempty `text` and nonempty `claims` of nonempty strings), admission (requires `input` nonempty, `decision` in `DECISIONS = ("ADMITTED","NOT_ADMITTED","UNKNOWN")`, nonempty `rationale`), `parse_condition` (split on first `=`; claims split on `,` stripped), `admissions`, `conditions`.
- [ ] **Step 4:** CLI flags and `admit` subcommand in `__main__.py`; update `schema/lab/consent.schema.json` (new actions, optional `drafted_by`, `ai_assisted`, `recorded_by`, `conditions`, `input`, `decision`, `rationale`).
- [ ] **Step 5:** Tests pass (`python -m unittest discover -s tests`); commit `feat(lab): consent provenance, conditions, admission and review_ack`.

### Task 3: Admission gate, NOT_ADMITTED non-verdicts, conditions in package and report

**Files:**
- Modify: `conformance/lab/kinds/verification.py`, `conformance/lab/runner.py`, `conformance/lab/package.py`, `conformance/lab/report.py`, `conformance/lab/rerun.py` (rerun passes recorded admissions)
- Test: `tests/lab/test_tracks_manual.py` (new)

**Interfaces:**
- Consumes: `consent.admissions`, `consent.conditions` (Task 2).
- Produces: `verification.execute(run_dir, scope, trees, admitted: dict[str, bool] | None = None)` — `None` means all admitted (adequacy, rerun of old packages). Claims over a non-admitted input get `{"execution": "NOT_ADMITTED", "result": None, "evidence": [], "verifier_error": {"code": "not_admitted", "message": <rationale>}}`.
- `runner.run` for track M verification: refuses (`GateError`) unless every scope input has an admission event; writes `results/admission.json` = `{"note": ..., "inputs": {id: {"decision", "who", "ref", "consent_index"}}}`. Rerun reads `results/admission.json` if present and passes the same map (so a rerun reproduces non-verdicts).
- `package.build` refuses a condition whose `claims` are empty or name an unknown claim id (adequacy: row ids).
- `report.render_report(scope, plan, results, conditions=None)` renders, per claim, "Conditions from scope confirmation" with `who` and text.

- [ ] **Step 1: Failing tests** `tests/lab/test_tracks_manual.py`:

```python
from conformance.lab import consent, lifecycle, runner
from conformance.lab.canonical import read_json
from conformance.lab.errors import GateError, PackageError
from tests.lab.helpers import AGREE_REF, NOW, LabTest, frozen_run

def admit(run, input_id, decision="ADMITTED"):
    consent.add(run, "tester", "admission", AGREE_REF, NOW, input=input_id, decision=decision, rationale="checked")

class AdmissionTest(LabTest):
    def setUp(self):
        super().setUp()
        self.run = frozen_run(self, "toy-verification-run", "toy-receipts")

    def test_run_refused_without_admission(self):
        admit(self.run, "within")
        with self.assertRaisesRegex(GateError, "over"):
            runner.run(self.run, NOW)

    def test_not_admitted_and_unknown_are_non_verdicts(self):
        admit(self.run, "within"); admit(self.run, "over", "UNKNOWN")
        runner.run(self.run, NOW)
        recs = read_json(self.run / "results/claims.json")["records"]
        over = [r for r in recs if r["input"] == "over"]
        self.assertTrue(over and all(r["execution"] == "NOT_ADMITTED" and r["result"] is None for r in over))
        self.assertTrue(any(r["result"] for r in recs if r["input"] == "within"))
        self.assertEqual(read_json(self.run / "results/admission.json")["inputs"]["over"]["decision"], "UNKNOWN")

class ConditionTest(LabTest):
    def run_with_condition(self, claims):
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        consent.add(run, "tester", "review_ack", AGREE_REF, NOW)  # satisfies no gate
        events = consent.load(run)
        # conditions are recorded at scope_agreed; append one more scope_agreed with a condition
        consent.add(run, "maintainer", "scope_agreed", AGREE_REF, NOW, conditions=[{"text": "test keys only", "claims": claims}])
        admit(run, "within"); admit(run, "over")
        runner.run(run, NOW)
        return run

    def test_unknown_claim_refused_at_package(self):
        run = self.run_with_condition(["nope"])
        with self.assertRaisesRegex(PackageError, "nope"):
            lifecycle.package(run, NOW)

    def test_condition_rendered_under_claim(self):
        run = self.run_with_condition(["exact_call"])
        lifecycle.package(run, NOW)
        report = (run / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("test keys only", report)
        self.assertIn("maintainer", report)
```

- [ ] **Step 2:** Run → fail.
- [ ] **Step 3:** Implement as in Interfaces. In `runner.run`, compute `admitted` only when `scope.get("track", "manual") == "manual"` and kind is verification (S is handled in Task 6). Add `"NOT_ADMITTED"` to rerun `_comparable` (already generic). In `report._verification_sections`, after the results table add a "## Claim conditions" section listing each claim id with its conditions; claims without conditions are omitted.
- [ ] **Step 4:** Existing tests that run verification runs (`test_package_rerun`, `test_lifecycle`) need admissions: add `admit` calls via a helper `admit_all(run)` in `tests/lab/helpers.py` and call it in `frozen_run` only when the fixture is a verification run. Full suite passes.
- [ ] **Step 5:** Commit `feat(lab): admission gate and claim conditions`.

### Task 4: Per-claim independence and REPRODUCTION

**Files:**
- Modify: `conformance/lab/scope.py`, `schema/lab/scope.schema.json`, `conformance/lab/report.py`
- Create: `conformance/lab/independence.py`
- Test: `tests/lab/test_independence.py`

**Interfaces:**
- `scope.INDEPENDENCE` adds `"REPRODUCTION"`. Optional `runner_authored: [str]` (may be empty). Claim optional `independent: bool`; `independent: false` requires nonempty `not_independent_reason`.
- `independence.FEDERATION = {"SELF_RUN": "AUTHOR_RUN", "REPRODUCTION": "REPRODUCTION", "SECOND_IMPLEMENTATION": "SECOND_IMPLEMENTATION", "INDEPENDENT_IMPLEMENTATION": "INDEPENDENT_IMPLEMENTATION"}`
- `independence.BCR = {"SELF_RUN": "BCR-0", "REPRODUCTION": "BCR-1", "SECOND_IMPLEMENTATION": "BCR-2", "INDEPENDENT_IMPLEMENTATION": "BCR-3 at most"}`
- `independence.per_claim(scope) -> dict[str, dict]` → `{claim_id: {"independent": bool, "reason": str}}` (adequacy: keyed by row id). Rule: independent iff run label is `INDEPENDENT_IMPLEMENTATION` and claim does not say `independent: false`; reason is the claim's reason or `"run label <X>"`.

- [ ] **Step 1: Failing tests:**

```python
import copy, json, unittest
from conformance.lab import independence
from conformance.lab.scope import validate_scope
from conformance.lab.errors import ScopeError
from tests.lab.helpers import FIXTURES

def ver():
    return json.loads((FIXTURES / "toy-verification-run" / "SCOPE.json").read_text(encoding="utf-8"))

class IndependenceTest(unittest.TestCase):
    def test_reproduction_is_valid_label(self):
        s = ver(); s["independence"] = "REPRODUCTION"; validate_scope(s)

    def test_claim_override_needs_reason(self):
        s = ver(); s["claims"][0]["independent"] = False
        with self.assertRaises(ScopeError):
            validate_scope(s)
        s["claims"][0]["not_independent_reason"] = "runner authored the cap fixture"
        validate_scope(s)
        pc = independence.per_claim(s)
        self.assertFalse(pc["cap_compliance"]["independent"])
        self.assertTrue(pc["exact_call"]["independent"])

    def test_non_independent_label_applies_to_all(self):
        s = ver(); s["independence"] = "SECOND_IMPLEMENTATION"; s.pop("independence_statement")
        self.assertFalse(any(v["independent"] for v in independence.per_claim(s).values()))

    def test_mapping(self):
        self.assertEqual(independence.FEDERATION["SELF_RUN"], "AUTHOR_RUN")
        self.assertEqual(independence.BCR["REPRODUCTION"], "BCR-1")
```

- [ ] **Step 2:** Run → fail. **Step 3:** Implement; report adds a "## Independence per claim" table (claim, independent yes/no, reason) and the federation/BCR labels next to the run label; `INDEPENDENCE_TEXT["REPRODUCTION"] = "REPRODUCTION. The runner reran the producer's own verifier; reproducibility, not implementation independence."`. Update schema; `test_schema_agreement` still passes.
- [ ] **Step 4:** Full suite; commit `feat(lab): per-claim independence and REPRODUCTION label`.

### Task 5: Offer reader

**Files:**
- Create: `conformance/lab/offer.py`, `schema/lab/offers.schema.json`, `templates/offers/aacp-offers.example.json`
- Test: `tests/lab/test_offer.py`

**Interfaces:**
- `offer.validate_offers(doc) -> dict` — raises `ScopeError` on schema problems or duplicate `offer_id`.
- `offer.find(doc, offer_id) -> dict` — raises `ScopeError` if absent.
- `offer.fetch_pinned(ref: dict, workdir) -> dict` — `ref = {"repo","commit","path","offer_id","sha256"}`; clones at commit (via `pins.fetch`), checks raw-byte sha256 of `path`, returns the offer entry.
- `offer.check_tip(ref, now: str, workdir) -> None` — clones default branch (`git clone --depth 1`, remote HEAD), raises `GateError` if file missing, entry missing, `revoked: true`, or `expires` (YYYY-MM-DD) < date of `now`.
- `offer.check_scope_against(scope, entry) -> None` — subject equality (repo, commit, sorted paths), inputs ⊆, claim ids ⊆, each claim's `claim_ceiling` equals offer's, kind in `entry["kinds"]`; raises `ScopeError` listing every problem.

- [ ] **Step 1: Failing tests** (`LabTest`, producer repo with `aacp-offers.json` built from a dict helper `make_offer(commit)`):

```python
class OfferTest(LabTest):
    def producer(self, offers, branch="main"):
        ...  # make_repo with files {"aacp-offers.json": json.dumps(offers)} on `branch`; returns url, commit, sha256

    def test_valid_offer_round_trip(self): ...
    def test_hash_mismatch_refused(self): ...
    def test_duplicate_offer_id_refused(self): ...
    def test_adequacy_kind_or_producer_code_refused(self): ...
    def test_after_review_needs_window(self): ...
    def test_tip_revoked_removed_expired(self): ...   # three sub-cases via new commits on default branch
    def test_tip_follows_default_branch(self): ...    # repo created with -b trunk
    def test_scope_mismatch_lists_every_problem(self): ...
```

Each test body asserts the exception type and a substring (`"duplicate"`, `"revoked"`, `"expired"`, `"sha256"`, `"subject"`, `"claim"`). `make_repo` gets an optional `branch="main"` parameter.

- [ ] **Step 2:** Run → fail. **Step 3:** Implement (stdlib; reuse `pins._git`, `pins.fetch`, `canonical.read_json`). **Step 4:** Tests pass; commit `feat(lab): producer-owned verification offers`.

### Task 6: Track S scope and lifecycle

**Files:**
- Modify: `conformance/lab/scope.py`, `conformance/lab/lifecycle.py`, `conformance/lab/plan.py`, `conformance/lab/state.py`, `conformance/lab/runner.py`, `conformance/lab/report.py`, `schema/lab/scope.schema.json`
- Test: `tests/lab/test_tracks_self_service.py`; fixture `tests/lab/fixtures/toy-offer-run/` (SCOPE with `track: self_service`, verifier copied from toy-verification-run)

**Interfaces:**
- `scope.track(scope) -> str` (`"manual"` default). For S: `offer` ref required; `agreement_parties`, `agreement_ref`, `publication.approvers` optional; `kind` must be `verification`; exactly one subject.
- `lifecycle.pin` (S): `offer.fetch_pinned` + `offer.check_scope_against`; stores `offer_entry_sha256` in STATE.
- `plan.require_agreement(run_dir, scope)` (S): no consent; calls `offer.check_tip`. `plan.freeze` (S): `published_ref` optional; second call without ref moves to FROZEN with `preregistered: False` recorded in STATE; with ref `preregistered: True`.
- `runner.run` (S): `offer.check_tip`; admission comes from the offer (`results/admission.json` decisions `ADMITTED` with `who: "offer:<offer_id>"`).
- `state.TRANSITIONS["SHARED_PRIVATE"]` adds `"PUBLISHED"`; `lifecycle.publish` guards: M unchanged (needs REVIEWED + every approver); S from SHARED_PRIVATE or REVIEWED when `check_tip` passes and: IMMEDIATE, or AFTER_REVIEW with `now >= shared_at + window` (refuse if `now < shared_at`); producer-maintainer `publication_declined` after share with HOLD → refuse; with PUBLISH_WITH_DISAGREEMENT → publish and STATUS lists the decline.
- `lifecycle.withhold` (S): allowed when HOLD and a producer-maintainer decline exists.
- `lifecycle.share` records `shared_at` (now) in STATE.
- `report.render_status` adds `"PUBLISHED_SELF_SERVICE": "PUBLISHED (self-service, unreviewed). Published under the producer's offer <id>; not reviewed and not endorsed."` and AFTER_REVIEW wording "no producer response within the window; not endorsed" when no review event exists.

- [ ] **Step 1: Failing tests** (`github` calls patched with `tests/lab/fake_gh.py` as in `test_github_flow.py`):

```python
class SelfServiceTest(LabTest):
    def test_full_immediate_flow_without_any_consent(self): ...     # pin, freeze (no ref), run, package, share, publish → PUBLISHED; CONSENT empty; STATUS says self-service, unreviewed
    def test_preregistered_flag(self): ...
    def test_adequacy_self_service_refused(self): ...
    def test_revoked_after_pin_blocks_freeze_and_run(self): ...
    def test_after_review_window(self): ...                         # publish refused at share+6d, allowed at share+7d
    def test_window_with_clock_before_share_refused(self): ...
    def test_decline_hold_and_disagreement(self): ...               # HOLD → publish refused, withhold ok; PUBLISH_WITH_DISAGREEMENT → published, STATUS names decline
    def test_manual_publish_unchanged(self): ...                    # M run cannot go SHARED_PRIVATE → PUBLISHED
```

- [ ] **Step 2:** Run → fail. **Step 3:** Implement. **Step 4:** Full suite; commit `feat(lab): self-service track under producer offers`.

### Task 7: Run capture and runner self-test

**Files:**
- Modify: `conformance/lab/runner.py`, `conformance/lab/__main__.py`, `conformance/lab/package.py` (workflow runs selftest), `conformance/lab/rerun.py` (capture not compared)
- Create: `conformance/lab/selftest.py`
- Test: `tests/lab/test_run_contract.py`

**Interfaces:**
- `runner.run(run_dir, now, workdir=None, argv=None)` writes `results/run-capture.json`: `{"argv": [...relative...], "started_at", "ended_at", "exit_status", "python", "platform"}`; `argv` entries that are absolute paths are replaced by paths relative to `run_dir` or `"<absolute path omitted>"`. Capture excluded from `NOT_COMPARED` comparison (add prefix `results/run-capture.json`).
- `__main__.main` computes exit status, then rewrites capture's `exit_status` before returning (run command only).
- `selftest.run_selftest(workdir=None) -> dict` → `{"nonzero_exit": bool, "no_results_written": bool, "no_success_line": bool}`: builds a throw-away S-free manual verification run in a temp dir with a verifier module whose function raises `SystemExit(0)`-free failure after setup **by making the subject unavailable after freeze** (delete the local remote) so `run` fails; invokes `__main__.main(["run", id], config=...)` capturing stdout; asserts each field separately.
- CLI: `selftest [--json]` prints the three fields; exit 0 only if all true.

- [ ] **Step 1: Failing tests:**

```python
class RunContractTest(LabTest):
    def test_capture_has_no_absolute_paths_and_exit(self): ...   # after main(["run", id]) capture exists, exit_status 0, no "/" prefix in argv, package leak scan passes
    def test_selftest_three_fields_true(self):
        from conformance.lab.selftest import run_selftest
        self.assertEqual(run_selftest(self.tmp), {"nonzero_exit": True, "no_results_written": True, "no_success_line": True})
    def test_selftest_detects_swallowing_wrapper(self): ...      # patch runner.run to return {} silently → nonzero_exit False
```

- [ ] **Step 2:** Run → fail. **Step 3:** Implement; WORKFLOW gains a step `python3 -c "import sys; sys.path.insert(0,'lab'); from conformance.lab.selftest import main; raise SystemExit(main([]))"` before rerun. **Step 4:** Full suite; commit `feat(lab): run capture and negative runner self-test`.

### Task 8: aacp run, next and export map

**Files:**
- Modify: `aacp/cli.py`
- Create: `aacp/lab_bridge.py` (next), `aacp/export.py`
- Test: `tests/test_cli_tracks.py`

**Interfaces:**
- `aacp run ...` → `conformance.lab.__main__.main(argv_after_run)`; its exit code is returned unchanged.
- `aacp.lab_bridge.next_actions(run_dir) -> dict` → `{"run_id", "track", "state", "outstanding": [{"kind": "mechanical"|"human", "who": str|None, "action": str, "why": str}], "next_command": str|None}`. Human items name the party (`who`) and are never phrased as a command for the operator to run as that party.
- `aacp next RUN [--json]` wraps it in the `aacp-command-result-v1` envelope (`verification_status: NOT_RUN`, `property_verdict: null`).
- `aacp.export.evidence_record(run_dir, include_unpublished=False) -> dict`; `aacp export map RUN --out DIR [--include-unpublished]` writes `DIR/evidence/<run_id>.yaml` (refuses to overwrite).
  Fields: `id, type, source, record_state, runner, runner_authored, independent_for, not_independent_for, results_as_emitted (published only), reviews, note, format_ref`. `format_ref` = `"aeoess/agent-governance-vocabulary#187@<head commit>"` constant `MAP_FORMAT_REF` in `aacp/export.py`.

- [ ] **Step 1: Failing tests:**

```python
class CliTracksTest(LabTest):
    def test_run_passthrough_status(self): ...
    def test_next_manual_lists_parties_not_operator_commands(self): ...  # SCOPED manual run: outstanding has human scope_agreed for "tester"; envelope validates
    def test_next_self_service_has_no_human_items(self): ...
    def test_export_refuses_unpublished(self): ...
    def test_export_unpublished_omits_results(self): ...
    def test_export_published_self_service(self): ...   # record_state "published, unreviewed", results_as_emitted counts, no owner_confirmation key
    def test_export_old_scope_defaults(self): ...        # scope without runner_authored / per-claim independence
```

- [ ] **Step 2:** Run → fail. **Step 3:** Implement. Get the #187 head commit with `gh pr view 187 -R aeoess/agent-governance-vocabulary --json headRefOid` and hard-code it. **Step 4:** Full suite; commit `feat(aacp): run, next and map export`.

### Task 9: Documentation

**Files:**
- Create: `docs/FEDERATION-TRACKS.md`
- Modify: `AGENTS.md`, `RUN-PROTOCOL-v0.3.md` (new §9 Tracks), `docs/CLI-ONBOARDING.md` (Next slices), `CHANGELOG.md`, `templates/scopes/README.md`

- [ ] **Step 1:** `docs/FEDERATION-TRACKS.md`: choosing a track (table from spec §3–4), producer guide for writing an offer (with example), runner guide (S and M command sequences), what each record does not establish, AI disclosure rules, how map export relates to #187 (prototype, not adopted).
- [ ] **Step 2:** AGENTS.md: add "Choose a track" step and the rule that agents may draft but never record another person's event.
- [ ] **Step 3:** Full suite + `python -m conformance.check`; commit `docs: federation tracks guide`.
