"""Run contract: contemporaneous capture of every run attempt, and a negative runner
self-test that reports nonzero exit, no results and no success line separately."""

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

from conformance.lab import lifecycle
from conformance.lab.__main__ import main
from conformance.lab.canonical import read_json
from conformance.lab.selftest import run_selftest
from tests.lab.helpers import NOW, LabTest, frozen_run


class CaptureTest(LabTest):
    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv), config={"org": "Example-Org", "runs_dir": self.tmp / "runs"})
        return code, out.getvalue()

    def test_every_attempt_is_captured_without_absolute_paths(self):
        run = frozen_run(self, "toy-verification-run", "toy-receipts", admit=False)
        code, _ = self.cli("run", "toy-verification")  # refused: no admission
        self.assertEqual(code, 2)
        from tests.lab.helpers import admit_all
        admit_all(run)
        code, out = self.cli("run", "toy-verification")
        self.assertEqual(code, 0, out)
        attempts = read_json(run / "RUN-CAPTURE.json")["attempts"]
        self.assertEqual([a["exit_status"] for a in attempts], [2, 0])
        self.assertIn("admission", attempts[0]["error"])
        for attempt in attempts:
            self.assertEqual(attempt["argv"], ["run", "toy-verification"])
            self.assertIn(attempt["cwd_relative_to_workspace"], ("<outside the lab workspace>",))
            self.assertIn(attempt["procedure_revision"]["source"], ("git", "vendored"))
            self.assertTrue(attempt["started_at"] <= attempt["ended_at"])
            self.assertNotIn(str(self.tmp), str(attempt))
        lifecycle.package(run, NOW)  # leak scan passes and the capture is in the manifest
        self.assertIn("RUN-CAPTURE.json", read_json(run / "MANIFEST.json")["files"])
        self.assertIn("conformance.lab selftest", (run / ".github" / "workflows" / "rerun.yml").read_text())
        import json, os, subprocess
        env = {**os.environ, "PYTHONPATH": str(run / "lab")}
        done = subprocess.run([sys.executable, "-m", "conformance.lab", "selftest", "--json"], cwd=run,
                              env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), {"nonzero_exit": True, "no_results_written": True,
                                                   "no_success_line": True})
        self.assertIn("lab", subprocess.run([sys.executable, "-c", "import sys; print(sys.path)"],
                                            env=env, capture_output=True, text=True).stdout)


class SelftestTest(unittest.TestCase):
    def test_lab_cli_fails_closed(self):
        self.assertEqual(run_selftest(), {"nonzero_exit": True, "no_results_written": True, "no_success_line": True})

    def test_detects_a_wrapper_that_swallows_failure(self):
        swallow = [sys.executable, "-c", "print('measured')"]
        result = run_selftest(command=swallow)
        self.assertFalse(result["nonzero_exit"])
        self.assertFalse(result["no_success_line"])
        self.assertTrue(result["no_results_written"])  # reported separately, never collapsed


if __name__ == "__main__":
    unittest.main()
