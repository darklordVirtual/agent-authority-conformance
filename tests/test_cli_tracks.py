"""aacp run / next / export map over lab runs."""

import contextlib
import io
import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from unittest import mock

import yaml

from aacp.cli import main, validator
from aacp.tracks import MAP_FORMAT_REF, evidence_record, next_actions
from conformance.lab import consent, lifecycle, runner
from conformance.lab.canonical import read_json, write_json
from tests.lab.helpers import AGREE_REF, NOW, LabTest, frozen_run, prepare_run, self_service_run

FAKE_GH = Path(__file__).resolve().parent / "lab" / "fake_gh.py"
ORG = "Runner-Org"


class CliTracksTest(LabTest):
    def setUp(self):
        super().setUp()
        self.gh_state = self.tmp / "gh.json"
        self.gh_state.write_text(json.dumps({"owners": {ORG: "Organization"}, "repos": {}, "calls": []}))
        env = {"AAC_GH": f"{shlex.quote(sys.executable)} {shlex.quote(str(FAKE_GH))}",
               "FAKE_GH_STATE": str(self.gh_state), "AAC_GIT_REMOTE_BASE": str(self.tmp / "github")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.tmp / "lab.toml").write_text(f'org = "{ORG}"\nruns_dir = "runs"\n', encoding="utf-8")
        old = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, old)

    def cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(argv))
        return code, out.getvalue()

    def envelope(self, *argv):
        code, out = self.cli(*argv, "--json")
        result = json.loads(out)
        validator("aacp-command-result-v1.schema.json").validate(result)
        self.assertEqual((result["verification_status"], result["property_verdict"]), ("NOT_RUN", None))
        return code, result

    def published_self_service(self):
        run, _ = self_service_run(self)
        lifecycle.pin(run)
        lifecycle.freeze(run, NOW, not_preregistered=True)
        runner.run(run, NOW)
        lifecycle.package(run, NOW)
        lifecycle.share(run, ORG, [], NOW)
        lifecycle.publish(run, NOW)
        return run

    def test_run_gate_refusals_reach_stderr(self):
        prepare_run(self)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = main(["run", "freeze", "toy"])
        self.assertEqual(code, 2)
        self.assertIn("error:", err.getvalue())

    def test_run_passthrough_status(self):
        prepare_run(self)
        code, out = self.cli("run", "status", "toy")
        self.assertEqual((code, out.strip()), (0, "SCOPED"))
        self.assertEqual(self.cli("run", "status", "missing")[0], 2)

    def test_next_manual_lists_parties_not_operator_commands(self):
        run = prepare_run(self)
        scope = read_json(run / "SCOPE.json")
        scope["agreement_parties"] = ["tester", "maintainer"]
        write_json(run / "SCOPE.json", scope)
        lifecycle.pin(run)
        consent.add(run, "tester", "scope_agreed", AGREE_REF, NOW)
        code, result = self.envelope("next", "toy")
        self.assertEqual(code, 0)
        human = [i for i in result["data"]["outstanding"] if i["kind"] == "human"]
        self.assertIn({"kind": "human", "who": "maintainer", "action": "scope_agreed",
                       "why": "each agreement party confirms the scope; conditions may be attached"}, human)
        self.assertNotIn("tester", [i["who"] for i in human if i["action"] == "scope_agreed"])
        self.assertIsNone(result["next_action"]["command"])  # waiting on people, not on a command
        for item in human:
            self.assertNotIn("--who", item["why"])

    def test_next_manual_frozen_asks_for_admission(self):
        frozen_run(self, "toy-verification-run", "toy-receipts", admit=False)
        data = next_actions(self.tmp / "runs" / "toy-verification")
        actions = {(i["kind"], i["action"]) for i in data["outstanding"]}
        self.assertIn(("human", "admission of within"), actions)
        self.assertIsNone(data["next_command"])

    def test_next_self_service_has_no_human_items(self):
        run, _ = self_service_run(self)
        lifecycle.pin(run)
        data = next_actions(run)
        self.assertEqual(data["track"], "self_service")
        self.assertFalse([i for i in data["outstanding"] if i["kind"] == "human"])
        self.assertIn("freeze toy-offer", data["next_command"])

    def test_export_refuses_unpublished(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        runner.run(run, NOW)
        code, _ = self.cli("export", "map", "toy-verification", "--out", str(self.tmp / "map"))
        self.assertEqual(code, 2)
        self.assertFalse((self.tmp / "map").exists())

    def test_export_unpublished_omits_results(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        runner.run(run, NOW)
        record = evidence_record(run, include_unpublished=True)
        self.assertEqual(record["record_state"], "private, not published")
        self.assertNotIn("results_as_emitted", record)
        self.assertNotIn("owner_confirmation", record)

    def test_export_published_self_service(self):
        self.published_self_service()
        code, _ = self.cli("export", "map", "toy-offer", "--out", str(self.tmp / "map"))
        self.assertEqual(code, 0)
        record = yaml.safe_load((self.tmp / "map" / "evidence" / "toy-offer.yaml").read_text(encoding="utf-8"))
        self.assertEqual(record["type"], "self_service_run")
        self.assertEqual(record["record_state"], "published, unreviewed")
        self.assertEqual(record["results_as_emitted"], {"ESTABLISHED": 2, "CONTRADICTED": 2, "NOT_ESTABLISHED": 1})
        self.assertEqual(record["runner"], "runner-a")
        self.assertEqual(record["runner_authored"], ["verifier/receipts.py"])
        self.assertEqual(record["independent_for"], [])
        self.assertTrue(all("SECOND_IMPLEMENTATION" in x for x in record["not_independent_for"]))
        self.assertEqual(record["format_ref"], MAP_FORMAT_REF)
        self.assertNotIn("owner_confirmation", record)
        self.assertIn("toy-receipts-v1", record["note"])
        self.assertEqual(self.cli("export", "map", "toy-offer", "--out", str(self.tmp / "map"))[0], 2)  # no overwrite

    def test_export_old_scope_defaults(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts")
        runner.run(run, NOW)
        lifecycle.package(run, NOW)
        lifecycle.share(run, ORG, [], NOW)
        consent.add(run, "maintainer", "review_ack", AGREE_REF, NOW, drafted_by="agent:claude", ai_assisted=True)
        record = evidence_record(run, include_unpublished=True)
        self.assertEqual(record["runner_authored"], [])
        self.assertEqual(sorted(record["independent_for"]), ["cap_compliance", "exact_call", "signature"])
        self.assertEqual(record["reviews"][0]["kind"], "review_ack")
        self.assertIn("AI assistance", record["note"])


if __name__ == "__main__":
    unittest.main()
