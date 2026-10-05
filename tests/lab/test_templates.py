import unittest
from pathlib import Path

from conformance.lab import lifecycle
from conformance.lab.canonical import read_json
from conformance.lab.errors import GateError
from conformance.lab.scope import validate_scope
from tests.lab.helpers import NOW, LabTest

TEMPLATES = Path(__file__).resolve().parents[2] / "templates" / "scopes"


class TemplateTest(LabTest):
    def templates(self):
        return sorted(TEMPLATES.glob("*.json"))

    def test_templates_are_structurally_valid_drafts(self):
        self.assertTrue(self.templates())
        for path in self.templates():
            with self.subTest(template=path.name):
                scope = validate_scope(read_json(path))
                self.assertIsNone(scope["agreement_ref"])
                self.assertIn("DRAFT", scope["draft_note"])
                self.assertTrue(all(len(s["commit"]) == 40 for s in scope["subjects"]))
                self.assertTrue(scope["publication"]["private_first"])

    def test_template_cannot_be_frozen_without_agreement(self):
        for path in self.templates():
            with self.subTest(template=path.name):
                run_dir = lifecycle.init(self.tmp / "runs", path.stem, None, NOW, template=path)
                with self.assertRaises(GateError):
                    lifecycle.freeze(run_dir, NOW)


if __name__ == "__main__":
    unittest.main()
