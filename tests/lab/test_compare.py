"""Side-by-side comparison of two runs of the same bounded claims. Never combined."""

import json
import unittest

from conformance.lab import lifecycle, runner
from conformance.lab.canonical import find_forbidden_keys, read_json, write_json
from conformance.lab.compare import compare_runs
from conformance.lab.errors import LabError
from tests.lab.helpers import NOW, LabTest, frozen_run


class CompareTest(LabTest):
    def two_runs(self):
        a = frozen_run(self, "toy-verification-run", "toy-receipts")
        runner.run(a, NOW)
        lifecycle.package(a, NOW)
        b = self.tmp / "other" / "toy-verification"
        import shutil
        shutil.copytree(a, b)
        return a, b

    def test_rows_side_by_side_without_aggregation(self):
        a, b = self.two_runs()
        claims = read_json(b / "results" / "claims.json")
        claims["records"][0]["result"] = "NOT_ESTABLISHED"
        claims["records"][0]["unresolved_obligations"] = ["x"]
        write_json(b / "results" / "claims.json", claims)
        doc = compare_runs(a, b)
        self.assertEqual(find_forbidden_keys(doc), [])
        self.assertNotIn("agree", json.dumps(doc).lower().replace("agreement_parties", ""))
        self.assertTrue(doc["same_pinned_inputs"])
        changed = claims["records"][0]
        row = next(r for r in doc["rows"] if (r["input"], r["claim"]) == (changed["input"], changed["claim"]))
        self.assertEqual((row["a"], row["b"]), ("ESTABLISHED", "NOT_ESTABLISHED"))
        self.assertIn("not a verdict", doc["note"])
        self.assertEqual(doc["runs"][0]["track"], "manual")

    def test_different_pins_are_flagged(self):
        a, b = self.two_runs()
        scope = read_json(b / "SCOPE.json")
        scope["subjects"][0]["files_sha256"]["receipts/over.json"] = "0" * 64
        write_json(b / "SCOPE.json", scope)
        self.assertFalse(compare_runs(a, b)["same_pinned_inputs"])

    def test_needs_results(self):
        a, _ = self.two_runs()
        with self.assertRaises(LabError):
            compare_runs(a, self.tmp / "missing")


if __name__ == "__main__":
    unittest.main()
