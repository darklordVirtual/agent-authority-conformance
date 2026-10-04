import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from conformance.lab import consent, lifecycle, runner, state
from conformance.lab.__main__ import main
from conformance.lab.canonical import read_json, write_json
from conformance.lab.errors import GateError, PlanError
from tests.lab.helpers import AGREE_REF, NOW, PLAN_REF, LabTest, agree, frozen_run, prepare_run


class InitTest(LabTest):
    def test_skeleton_is_scoped_and_incomplete(self):
        run_dir = lifecycle.init(self.tmp / "runs", "new", "adequacy", NOW)
        self.assertEqual(state.load_state(run_dir)["state"], "SCOPED")
        with self.assertRaises(Exception):
            lifecycle.pin(run_dir)  # skeleton must be completed by a human first

    def test_init_refuses_existing_and_needs_kind(self):
        lifecycle.init(self.tmp / "runs", "new", "verification", NOW)
        with self.assertRaises(GateError):
            lifecycle.init(self.tmp / "runs", "new", "verification", NOW)
        with self.assertRaises(GateError):
            lifecycle.init(self.tmp / "runs", "other", None, NOW)

    def test_follow_up_inherits_faults_and_links_previous_plan(self):
        run_dir = frozen_run(self)
        previous_hash = state.load_state(run_dir)["plan_sha256"]
        follow = lifecycle.init(run_dir.parent, "toy-v2", None, NOW, follow_up="toy", commit="a" * 40)
        scope = read_json(follow / "SCOPE.json")
        self.assertEqual(scope["previous_run"], {"run_id": "toy", "plan_sha256": previous_hash})
        self.assertEqual(scope["subjects"][0]["files_sha256"], {})
        self.assertTrue((follow / "faults" / "known.json").is_file())
        self.assertEqual(read_json(follow / "CONSENT.json"), {"events": []})


class FreezeTest(LabTest):
    def setUp(self):
        super().setUp()
        self.run = prepare_run(self)
        lifecycle.pin(self.run)

    def test_pin_fills_hashes_and_is_refused_after_agreement(self):
        files = read_json(self.run / "SCOPE.json")["subjects"][0]["files_sha256"]
        self.assertEqual(sorted(files), ["cases.json", "checker.py"])
        agree(self.run)
        with self.assertRaisesRegex(GateError, "scope_agreed"):
            lifecycle.pin(self.run)

    def test_freeze_needs_every_party(self):
        scope = read_json(self.run / "SCOPE.json")
        scope["agreement_parties"] = ["tester", "maintainer"]
        write_json(self.run / "SCOPE.json", scope)
        agree(self.run, "tester")
        with self.assertRaisesRegex(GateError, "maintainer"):
            lifecycle.freeze(self.run, NOW)

    def test_freeze_needs_run_authorized(self):
        consent.add(self.run, "tester", "scope_agreed", AGREE_REF, NOW)
        with self.assertRaisesRegex(GateError, "run_authorized"):
            lifecycle.freeze(self.run, NOW)

    def test_two_step_freeze(self):
        agree(self.run)
        with self.assertRaisesRegex(GateError, "without --published-ref"):
            lifecycle.freeze(self.run, NOW, PLAN_REF)
        digest, frozen = lifecycle.freeze(self.run, NOW)
        self.assertFalse(frozen)
        self.assertEqual(state.load_state(self.run)["state"], "SCOPED")
        again, frozen = lifecycle.freeze(self.run, NOW, PLAN_REF)
        self.assertEqual((again, frozen), (digest, True))
        doc = state.load_state(self.run)
        self.assertEqual((doc["state"], doc["plan_published_ref"]), ("FROZEN", PLAN_REF))

    def test_changed_fault_after_hash_is_refused(self):
        agree(self.run)
        lifecycle.freeze(self.run, NOW)
        path = self.run / "faults" / "known.json"
        doc = read_json(path)
        doc["faults"][0]["class"] = "renamed"
        write_json(path, doc)
        with self.assertRaisesRegex(PlanError, "changed"):
            lifecycle.freeze(self.run, NOW, PLAN_REF)

    def test_non_unique_anchor_and_unparsable_replacement_are_refused(self):
        agree(self.run)
        path = self.run / "faults" / "known.json"
        doc = read_json(path)
        doc["faults"][0]["anchor"] = "return"
        doc["faults"][1]["replacement"] = "if False"
        write_json(path, doc)
        with self.assertRaises(PlanError) as ctx:
            lifecycle.freeze(self.run, NOW)
        self.assertIn("F1: anchor occurs", str(ctx.exception))
        self.assertIn("F2: replacement does not parse", str(ctx.exception))

    def test_agreement_ref_required(self):
        scope = read_json(self.run / "SCOPE.json")
        scope["agreement_ref"] = None
        write_json(self.run / "SCOPE.json", scope)
        agree(self.run)
        with self.assertRaisesRegex(GateError, "agreement_ref"):
            lifecycle.freeze(self.run, NOW)


class RunTest(LabTest):
    def test_run_requires_frozen(self):
        run_dir = prepare_run(self)
        with self.assertRaisesRegex(GateError, "FROZEN"):
            runner.run(run_dir, NOW)

    def test_toy_adequacy_end_to_end(self):
        run_dir = frozen_run(self)
        results = runner.run(run_dir, NOW)
        self.assertTrue(runner.has_survivors(results))
        row = read_json(run_dir / "results" / "row1.json")
        self.assertEqual(row["status"], "MEASURED")
        self.assertEqual(state.load_state(run_dir)["state"], "RUN")

    def test_toy_verification_end_to_end(self):
        run_dir = frozen_run(self, "toy-verification-run", "toy-receipts")
        runner.run(run_dir, NOW)
        records = read_json(run_dir / "results" / "claims.json")["records"]
        self.assertEqual(len(records), 5)
        self.assertTrue((run_dir / "results" / "agreement.json").is_file())

    def test_subject_changed_after_freeze_is_refused(self):
        run_dir = frozen_run(self)
        scope = read_json(run_dir / "SCOPE.json")
        scope["subjects"][0]["files_sha256"]["checker.py"] = "0" * 64
        write_json(run_dir / "SCOPE.json", scope)
        with self.assertRaises(Exception):
            runner.run(run_dir, NOW)
        self.assertEqual(state.load_state(run_dir)["state"], "FROZEN")


class CliTest(LabTest):
    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv), config={"org": "Example-Org", "runs_dir": self.tmp / "runs"})
        return code, out.getvalue(), err.getvalue()

    def test_cli_flow_to_run(self):
        prepare_run(self)
        self.assertEqual(self.cli("pin", "toy")[0], 0)
        for action in ("scope_agreed", "run_authorized"):
            self.assertEqual(self.cli("consent", "toy", "--who", "tester", "--action", action, "--ref", AGREE_REF)[0], 0)
        code, out, _ = self.cli("freeze", "toy")
        self.assertEqual(code, 0)
        self.assertIn("plan sha256:", out)
        self.assertEqual(self.cli("freeze", "toy", "--published-ref", PLAN_REF)[0], 0)
        self.assertEqual(self.cli("status", "toy")[1].strip(), "FROZEN")
        self.assertEqual(self.cli("run", "toy")[0], 1)  # survivors present

    def test_cli_condition_admission_and_provenance(self):
        run_dir = prepare_run(self)
        code, _, err = self.cli("consent", "toy", "--who", "maintainer", "--action", "scope_agreed",
                                "--ref", AGREE_REF, "--condition", "row-a=test keys only, = kept",
                                "--drafted-by", "agent:claude", "--ai-assisted", "--recorded-by", "operator")
        self.assertEqual(code, 0, err)
        code, _, err = self.cli("admit", "toy", "--input", "cases", "--decision", "NOT_ADMITTED",
                                "--rationale", "producer-authored expectations", "--who", "tester", "--ref", AGREE_REF)
        self.assertEqual(code, 0, err)
        first, second = consent.load(run_dir)
        self.assertEqual(first["conditions"], [{"claims": ["row-a"], "text": "test keys only, = kept"}])
        self.assertEqual((first["drafted_by"], first["ai_assisted"], first["recorded_by"]),
                         ("agent:claude", True, "operator"))
        self.assertEqual((second["action"], second["decision"], second["drafted_by"]),
                         ("admission", "NOT_ADMITTED", "human"))
        self.assertEqual(self.cli("consent", "toy", "--who", "x", "--action", "run_authorized",
                                  "--ref", AGREE_REF, "--condition", "a=b")[0], 2)

    def test_cli_errors_exit_two(self):
        code, _, err = self.cli("status", "missing")
        self.assertEqual(code, 2)
        self.assertIn("error:", err)


if __name__ == "__main__":
    unittest.main()
