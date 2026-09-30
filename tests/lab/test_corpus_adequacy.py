import json
import os
import shutil
import unittest
import unittest.mock

from conformance.lab.engines.corpus_adequacy import CorpusAdequacyEngine
from conformance.lab.errors import EngineError
from conformance.lab.faults import row_mutations
from conformance.lab.kinds import adequacy
from conformance.lab import lifecycle, runner
from conformance.lab.canonical import read_json, write_json
from tests.lab.helpers import NOW, PLAN_REF, FIXTURES, LabTest, agree, prepare_run


def toy():
    scope = json.loads((FIXTURES / "toy-run" / "SCOPE.json").read_text(encoding="utf-8"))
    row = scope["rows"][0]
    controls, faults = row_mutations(FIXTURES / "toy-run", scope, row)
    return scope, row, controls, faults


class ManifestTest(unittest.TestCase):
    def test_manifest_shape(self):
        _, row, controls, faults = toy()
        manifest = CorpusAdequacyEngine({}).manifest(row, controls, faults)
        self.assertEqual(manifest["implementation"], "checker.py")
        self.assertEqual(manifest["entrypoint_command"], ["python3", "-B", "case.py", "{vector}"])
        labels = [m["label"] for m in manifest["mutants"]["aac"]]
        self.assertEqual(labels, ["CONTROL-positive", "CONTROL-inert", "F1", "F2", "F3", "F4"])
        self.assertEqual(manifest["mutants"]["aac"][0]["control_polarity"], "positive")

    def test_one_implementation_file_only(self):
        _, row, controls, faults = toy()
        faults[0] = {**faults[0], "file": "other.py"}
        with self.assertRaisesRegex(EngineError, "one implementation file"):
            CorpusAdequacyEngine({}).manifest(row, controls, faults)

    def test_translation(self):
        t = CorpusAdequacyEngine.translate
        self.assertEqual(adequacy.classify(t("a", {"verdict": "killed", "how": "2 vector(s) moved", "moved": 2})), "killed")
        self.assertEqual(adequacy.classify(t("a", {"verdict": "killed", "how": "unexpected-exit"})), "killed_crash")
        self.assertEqual(adequacy.classify(t("a", {"verdict": "survived", "how": "no vector"})), "survived")
        self.assertEqual(adequacy.classify(t("a", {"verdict": "unproved"})), "not_measured")
        self.assertEqual(adequacy.row_status({"positive": t("p", {"verdict": "control-killed", "moved": 1}),
                                              "inert": t("i", {"verdict": "control-unchanged", "moved": 0})}),
                         "MEASURED")
        with self.assertRaises(EngineError):
            t("missing", None)

    def test_missing_checkout_is_an_engine_error(self):
        with unittest.mock.patch.dict(os.environ, {"AAC_CORPUS_ADEQUACY": ""}):
            engine = CorpusAdequacyEngine({"corpus_adequacy_path": "/nonexistent"})
            with self.assertRaisesRegex(EngineError, "AAC_CORPUS_ADEQUACY"):
                engine.identity()


@unittest.skipUnless(os.environ.get("AAC_CORPUS_ADEQUACY"), "set AAC_CORPUS_ADEQUACY to a pinned checkout")
class IntegrationTest(LabTest):
    def test_toy_matches_native_on_measured_faults(self):
        _, row, controls, faults = toy()
        tree = self.tmp / "tree"
        shutil.copytree(FIXTURES / "toy-subject", tree)
        adequacy.prepare_tree(FIXTURES / "toy-run", tree)
        measured = CorpusAdequacyEngine({}).measure(tree, row, controls, faults)
        outcomes = {o.fault_id: adequacy.classify(o) for o in measured["faults"]}
        self.assertEqual(outcomes["F1"], "killed")
        self.assertEqual(outcomes["F2"], "killed")
        self.assertEqual(outcomes["F3"], "survived")
        self.assertEqual(adequacy.row_status(measured["controls"]), "MEASURED")
        self.assertNotIn(str(self.tmp), json.dumps(measured["engine_report"]["report"]))

    def test_primary_corpus_adequacy_with_native_cross_check(self):
        run_dir = prepare_run(self)
        scope = read_json(run_dir / "SCOPE.json")
        scope["engine"] = {"name": "corpus_adequacy", "cross_check": "native"}
        write_json(run_dir / "SCOPE.json", scope)
        lifecycle.pin(run_dir)
        agree(run_dir)
        lifecycle.freeze(run_dir, NOW)
        lifecycle.freeze(run_dir, NOW, PLAN_REF)
        runner.run(run_dir, NOW)
        self.assertTrue((run_dir / ".local" / "engine" / "row1.original.json").is_file())
        cross = read_json(run_dir / "results" / "cross-check" / "row1.json")
        self.assertEqual(cross["secondary"], "native")
        lifecycle.package(run_dir, NOW)
        delivery = read_json(run_dir / "ORIGINAL-TO-DELIVERY.json")
        self.assertIn("results/engine/row1.json", delivery["files"])
        self.assertIn("Engine cross-check", (run_dir / "REPORT.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
