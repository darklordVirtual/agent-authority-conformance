import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

from aacp.cli import main, validator


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = main([*arguments, "--json"])
        result = json.loads(stdout.getvalue())
        validator("aacp-command-result-v1.schema.json").validate(result)
        self.assertEqual(result["verification_status"], "NOT_RUN")
        self.assertIsNone(result["property_verdict"])
        return status, result

    def test_onboarding_round_trip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aacp-project.yaml"
            code, result = self.run_cli("init", "--project", str(path), "--name", "example",
                                        "--role", "producer", "--role", "consumer")
            self.assertEqual(code, 0)
            document = result["data"]["project"]
            self.assertEqual(document["roles"], ["producer", "consumer"])
            self.assertEqual(document["execution"]["external_code"], "deny_by_default")
            self.assertEqual(document["review"]["publication"], "PRIVATE_UNTIL_APPROVED")
            original = path.read_bytes()
            self.assertEqual(self.run_cli("init", "--project", str(path))[0], 2)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(self.run_cli("validate", "--project", str(path))[0], 0)
            code, inspection = self.run_cli("inspect", "--project", str(path))
            self.assertEqual(code, 0)
            self.assertEqual(inspection["data"]["subject_pin"]["state"], "UNKNOWN")
            self.assertEqual(inspection["next_action"]["action"], "freeze_subject_pin")

    def test_invalid_missing_and_unsupported_input_are_json_non_verdicts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.yaml"
            code, result = self.run_cli("validate", "--project", str(path))
            self.assertEqual(code, 2)
            self.assertEqual(result["errors"][0]["code"], "MISSING_INPUT")
            for content in ["schema_version: unsupported\n", "schema_version: a\nschema_version: b\n",
                            "a: &anchor []\nb: *anchor\n", "!!python/object/apply:os.system ['false']",
                            "[invalid", "", "[" * 1000 + "]" * 1000,
                            "x" * (1024 * 1024 + 1)]:
                with self.subTest(content=content[:60]):
                    path.write_text(content, encoding="utf-8")
                    self.assertEqual(self.run_cli("validate", "--project", str(path))[0], 2)
            self.assertEqual(self.run_cli("run")[0], 2)
            self.assertEqual(self.run_cli("init", "--role", "administrator")[0], 2)

    def test_role_and_surface_contracts_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.yaml"
            self.run_cli("init", "--project", str(path))
            document = yaml.safe_load(path.read_text())
            surface = {"id": "gateway", "role": "consumer", "consumes": "tool-manifest-v1"}
            document["surfaces"] = [surface]
            path.write_text(yaml.safe_dump(document))
            self.assertEqual(self.run_cli("validate", "--project", str(path))[0], 0)
            for surfaces in [[surface, surface], [{"id": "tool", "role": "producer", "contract": "v1"}],
                             [{"id": "gateway", "role": "consumer"}]]:
                document["surfaces"] = surfaces
                path.write_text(yaml.safe_dump(document))
                self.assertEqual(self.run_cli("validate", "--project", str(path))[0], 2)
            document["surfaces"] = []
            document["execution"]["network"] = "allow"
            path.write_text(yaml.safe_dump(document))
            self.assertEqual(self.run_cli("validate", "--project", str(path))[0], 2)

    def test_inspect_does_not_execute_subject_or_fetch_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.yaml"
            self.run_cli("init", "--project", str(path))
            with patch("aacp.cli.subprocess.run") as git:
                git.return_value = subprocess.CompletedProcess([], 0, "a" * 40 + "\n", "")
                code, result = self.run_cli("inspect", "--project", str(path))
                self.assertEqual(code, 0)
                self.assertFalse(result["data"]["subject_pin"]["worktree_content_checked"])
                self.assertEqual(result["data"]["subject_pin"]["local_head"], "a" * 40)
                git.assert_called_once()
                arguments = git.call_args.args[0]
                self.assertEqual(arguments[-3:], ["rev-parse", "--verify", "HEAD"])
                self.assertIn("core.fsmonitor=false", arguments)

    def test_explicit_pin_mismatch_is_not_a_property_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.yaml"
            self.run_cli("init", "--project", str(path))
            document = yaml.safe_load(path.read_text())
            document["project"]["revision"] = "b" * 40
            path.write_text(yaml.safe_dump(document))
            with patch("aacp.cli.local_revision", return_value="a" * 40):
                code, result = self.run_cli("inspect", "--project", str(path))
            self.assertEqual(code, 0)
            self.assertEqual(result["data"]["subject_pin"]["state"], "MISMATCH")
            self.assertEqual(result["next_action"]["action"], "freeze_subject_pin")

    def test_module_entrypoint_emits_json_on_argument_error(self):
        result = subprocess.run([sys.executable, "-m", "aacp", "validate", "--unknown", "--json"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "INVALID_INPUT")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()