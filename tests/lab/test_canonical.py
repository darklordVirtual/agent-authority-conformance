import unittest

from conformance.lab import canonical
from conformance.lab.config import load_config
from conformance.lab.errors import LabError, ScopeError
from tests.lab.helpers import LabTest


class CanonicalTest(LabTest):
    def test_dumps_is_sorted_indented_and_newline_terminated(self):
        self.assertEqual(canonical.dumps({"b": 1, "a": "ø"}), '{\n  "a": "ø",\n  "b": 1\n}\n'.encode())

    def test_duplicate_keys_are_rejected(self):
        path = self.tmp / "dup.json"
        path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
        with self.assertRaises(ScopeError):
            canonical.read_json(path)

    def test_round_trip_and_hash(self):
        path = self.tmp / "x.json"
        canonical.write_json(path, {"k": [1, 2]})
        self.assertEqual(canonical.read_json(path), {"k": [1, 2]})
        self.assertEqual(canonical.sha256_file(path), canonical.sha256_json({"k": [1, 2]}))

    def test_forbidden_keys_found_at_any_depth(self):
        doc = {"rows": [{"counts": {"score": 1}}], "overall": "x"}
        self.assertEqual(sorted(canonical.find_forbidden_keys(doc)),
                         ["$.overall", "$.rows[0].counts.score"])

    def test_lab_errors_exit_two(self):
        self.assertEqual(ScopeError("x").exit_code, 2)
        self.assertTrue(issubclass(ScopeError, LabError))

    def test_config_reads_lab_toml(self):
        (self.tmp / "lab.toml").write_text('org = "Example-Org"\nruns_dir = "r"\n', encoding="utf-8")
        cfg = load_config(self.tmp)
        self.assertEqual(cfg["org"], "Example-Org")
        self.assertEqual(cfg["runs_dir"], self.tmp / "r")

    def test_repository_config_names_the_run_organisation(self):
        self.assertEqual(load_config()["org"], "R-research-lab")


if __name__ == "__main__":
    unittest.main()
