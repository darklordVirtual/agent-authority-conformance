import json
import os
import subprocess
import sys
import unittest

from conformance.lab import lifecycle, package, runner, state
from conformance.lab.canonical import read_json, write_json
from conformance.lab.errors import PackageError
from tests.lab.helpers import NOW, LabTest, frozen_run


def run_rerun(pkg):
    result = subprocess.run([sys.executable, "-B", str(pkg / "rerun.py")], capture_output=True, text=True,
                            env={**os.environ, "PYTHONPATH": ""})
    return result.returncode, result.stdout.strip(), result.stderr


class PackageTest(LabTest):
    def build(self, fixture="toy-run", subject="toy-subject"):
        run_dir = frozen_run(self, fixture, subject)
        runner.run(run_dir, NOW)
        lifecycle.package(run_dir, NOW)
        return run_dir

    def test_package_contents(self):
        pkg = self.build()
        for name in ("REPORT.md", "STATUS.md", "NOTICE", "REPRODUCE.md", "MANIFEST.json", "rerun.py",
                     "RUN-PLAN-FROZEN.json", "SCOPE.json", "CONSENT.json", ".github/workflows/rerun.yml",
                     "lab/conformance/lab/rerun.py", "results/row1.json"):
            self.assertTrue((pkg / name).is_file(), name)
        self.assertEqual(state.load_state(pkg)["state"], "PACKAGED")
        manifest = read_json(pkg / "MANIFEST.json")["files"]
        self.assertIn("results/row1.json", manifest)
        self.assertNotIn("STATE.json", manifest)

    def test_report_labels_and_never_aggregates(self):
        pkg = self.build()
        report = (pkg / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("SELF_RUN", report)
        self.assertIn("not a checker defect", report)
        self.assertIn("`F3` (toy-known, guard_removal)", report)
        self.assertIn("Crash kills:", report)
        for word in ("%", "score", "overall", "Total", "adequate"):
            self.assertNotIn(word, report.replace("no percentage headline", ""))
        status = (pkg / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("not citable", status)

    def test_verification_report_separates_agreement(self):
        report = (self.build("toy-verification-run", "toy-receipts") / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("INDEPENDENT_IMPLEMENTATION", report)
        self.assertIn("Agreement with the producer's expectations (not a result)", report)

    def test_leak_scan(self):
        for text, label in (("token ghp_" + "a" * 30, "GitHub token"),
                            ("mail someone@example.com", "e-mail"),
                            ("path /Users/someone/project", "local absolute path")):
            root = self.tmp / label.replace(" ", "-")
            (root / "adapter").mkdir(parents=True)
            (root / "adapter" / "x.py").write_text(text, encoding="utf-8")
            with self.subTest(label=label), self.assertRaisesRegex(PackageError, label):
                package.scan_for_leaks(root)

    def test_leak_scan_allows_licence_contact_addresses(self):
        (self.tmp / "UPSTREAM-LICENSE-0.txt").write_text("contact licensing@example.com", encoding="utf-8")
        package.scan_for_leaks(self.tmp)

    def test_rerun_reproduced(self):
        pkg = self.build()
        code, out, err = run_rerun(pkg)
        self.assertEqual((code, out), (0, "REPRODUCED"), err)
        self.assertEqual(len(list((pkg / "reruns").glob("rerun-*.json"))), 1)

    def test_rerun_verification_reproduced(self):
        pkg = self.build("toy-verification-run", "toy-receipts")
        code, out, err = run_rerun(pkg)
        self.assertEqual((code, out), (0, "REPRODUCED"), err)

    def test_rerun_diverged_when_results_disagree(self):
        pkg = self.build()
        result = read_json(pkg / "results" / "row1.json")
        f3 = next(m for m in result["mutants"] if m["fault_id"] == "F3")
        f3.update(outcome="killed", moved=1)
        write_json(pkg / "results" / "row1.json", result)
        package.write_manifest(pkg)
        code, out, err = run_rerun(pkg)
        self.assertEqual((code, out), (1, "DIVERGED"))
        self.assertIn("mutant F3", err)

    def test_rerun_not_reproducible_when_manifest_breaks(self):
        pkg = self.build()
        (pkg / "results" / "row1.json").write_text("{}", encoding="utf-8")
        code, out, err = run_rerun(pkg)
        self.assertEqual((code, out), (2, "NOT_REPRODUCIBLE"))
        self.assertIn("changed results/row1.json", err)

    def test_rerun_not_reproducible_for_unlisted_file(self):
        pkg = self.build()
        (pkg / "adapter" / "extra.py").write_text("x = 1\n", encoding="utf-8")
        code, out, err = run_rerun(pkg)
        self.assertEqual(code, 2)
        self.assertIn("unlisted adapter/extra.py", err)

    def test_package_requires_run_state(self):
        run_dir = frozen_run(self)
        with self.assertRaises(Exception):
            lifecycle.package(run_dir, NOW)


if __name__ == "__main__":
    unittest.main()
