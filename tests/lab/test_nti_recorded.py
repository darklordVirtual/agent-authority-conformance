"""The recorded NTI run (templates/runs/nti-witness/recorded/RECORD.json).

Offline checks run everywhere: the record belongs to the committed verifier and skeleton
scope, covers exactly the declared claims and probes, and says what the PR says it says.
The real-byte check fetches the two pinned NTI commits and reruns the scope; it runs when
AACP_NETWORK_TESTS=1 (the nti-real-bytes CI job sets it).
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from conformance.lab import lifecycle, runner
from conformance.lab.canonical import find_forbidden_keys, read_json, sha256_file

ROOT = Path(__file__).resolve().parents[2]
SKELETON = ROOT / "templates" / "runs" / "nti-witness"
NOW = "2026-11-07T12:00:00Z"
NETWORK = os.environ.get("AACP_NETWORK_TESTS") == "1"


def record():
    return read_json(SKELETON / "recorded" / "RECORD.json")


class RecordedOfflineTest(unittest.TestCase):
    def setUp(self):
        self.record, self.scope = record(), read_json(SKELETON / "SCOPE.json")

    def test_record_belongs_to_the_committed_verifier_and_scope(self):
        self.assertEqual(self.record["template_scope_sha256"], sha256_file(SKELETON / "SCOPE.json"),
                         "SCOPE.json changed: make a new run and a new record")
        self.assertEqual(self.record["run_files"],
                         {"verifier/nti_witness.py": sha256_file(SKELETON / "verifier" / "nti_witness.py")},
                         "the verifier changed: make a new run and a new record")

    def test_record_pins_the_scope_subjects_and_boundary(self):
        self.assertEqual([(s["repo"], s["commit"]) for s in self.record["subjects"]],
                         [(s["repo"], s["commit"]) for s in self.scope["subjects"]])
        boundary = self.record["public_boundary"]
        self.assertEqual(boundary["commit"], self.record["subjects"][0]["commit"])
        self.assertEqual(self.record["subjects"][0]["files_sha256"][boundary["path"]], boundary["sha256"])
        for subject, declared in zip(self.record["subjects"], self.scope["subjects"]):
            self.assertTrue(subject["files_sha256"])
            for path in subject["files_sha256"]:
                self.assertTrue(any(path == d or path.startswith(d.rstrip("/") + "/") for d in declared["paths"]), path)

    def test_record_covers_exactly_the_declared_claims_and_probes(self):
        declared = sorted((c["id"], i) for c in self.scope["claims"] for i in c["inputs"])
        self.assertEqual(sorted((r["claim"], r["input"]) for r in self.record["claims"]), declared)
        self.assertEqual([r["probe"] for r in self.record["probes"]], [p["id"] for p in self.scope["probes"]])
        schema = json.loads((ROOT / "schema" / "lab" / "probe-results.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate({"note": "recorded", "records": self.record["probes"]})
        self.assertEqual(find_forbidden_keys(self.record), [])

    def test_recorded_results(self):
        results = {(r["claim"], r["input"]): r["result"] for r in self.record["claims"]}
        for claim in ("package_signature", "s6_seal"):
            for input_id in ("witness", "pages"):
                self.assertEqual(results[(claim, input_id)], "ESTABLISHED")
        for claim in ("s4_digests", "s5_root", "manifest_hashes", "pages_mirror"):
            self.assertEqual(results[(claim, "tree")], "ESTABLISHED")
        for claim in ("suite_outcomes_evidenced", "key_anchor"):
            self.assertEqual(results[(claim, "tree")], "NOT_ESTABLISHED")
        probes = {r["probe"]: r for r in self.record["probes"]}
        self.assertTrue(all(r["observation"] == "DEMONSTRATED" for r in probes.values()))
        self.assertFalse(probes["s5_documented_vs_implemented"]["affects_pinned_artifact"])
        self.assertFalse(probes["s5_leaf_count_binding"]["affects_pinned_artifact"])
        s5 = probes["s5_documented_vs_implemented"]["witness"]
        self.assertEqual(s5["leaf_counts_where_roots_differ_1_to_8"], [3, 5, 6, 7])
        self.assertTrue(s5["published_root_same_under_both_rules"])
        terms = probes["s4_s5_s6_meaning_changed"]
        self.assertEqual(terms["class"], "TERMINOLOGY_CHANGE")
        self.assertIn("says nothing about where the construction or any code came from", terms["message"])


@unittest.skipUnless(NETWORK, "set AACP_NETWORK_TESTS=1 to rerun the scope over the real pinned NTI bytes")
class RecordedRealBytesTest(unittest.TestCase):
    def test_fresh_run_over_the_real_pins_reproduces_the_record(self):
        expected = record()
        with tempfile.TemporaryDirectory(prefix="aac nti ") as tmp:
            run = lifecycle.init(Path(tmp) / "runs", "nti-witness", None, NOW, template=SKELETON / "SCOPE.json")
            scope = lifecycle.pin(run)
            self.assertEqual([s["files_sha256"] for s in scope["subjects"]],
                             [s["files_sha256"] for s in expected["subjects"]])
            lifecycle.freeze(run, NOW, not_preregistered=True)
            runner.run(run, NOW)
            self.assertEqual(read_json(run / "results" / "claims.json")["records"], expected["claims"])
            self.assertEqual(read_json(run / "results" / "probes.json")["records"], expected["probes"])


if __name__ == "__main__":
    unittest.main()
