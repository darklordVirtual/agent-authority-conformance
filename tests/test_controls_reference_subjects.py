"""Every reference subject under tests/controls_reference/ is run through conformance.controls.

A reference subject shows that a catalog control's probe contract is
probe-able: the probe observes the weakness on the weak subject, stops observing
it when that weakness alone is repaired (DISCRIMINATES), and observes it again
when the protection alone is removed from the protected subject (SENSITIVE). A
contract that no probe can satisfy on a 30-line subject is not a usable control.

Nothing here is a finding about any project. See tests/controls_reference/README.md.
"""
import contextlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from conformance import controls
from conformance.validation import ROOT, validate_assessment

CATALOG = "controls/aacp-controls-v1.3.0/catalog.json"
REFERENCE = ROOT / "tests" / "controls_reference"
REFERENCE_DIRS = sorted(d for d in REFERENCE.iterdir() if d.is_dir() and (d / "weak.py").is_file())
PYTHON_ONLY_ORIGIN = "aacp:reference-subject"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   cwd=cwd, check=True, capture_output=True)


def head(cwd):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True).stdout.strip()


def load_reference(d: pathlib.Path):
    weak = (d / "weak.py").read_text(encoding="utf-8")
    repair = json.loads((d / "repair.json").read_text(encoding="utf-8"))
    protected = controls.apply_mutation(weak, repair)  # ValueError if the anchor is not unique
    return weak, protected, repair


class Subject:
    """A throwaway git checkout holding `subject.py`, plus a binding that installs the probe."""

    def __init__(self, tmp: pathlib.Path, control: dict, source: str, probe: pathlib.Path):
        self.dir = tmp / "subject"
        self.dir.mkdir()
        (self.dir / "subject.py").write_text(source, encoding="utf-8")
        git(self.dir, "init", "-q")
        git(self.dir, "add", ".")
        git(self.dir, "commit", "-qm", "subject")
        self.rev = head(self.dir)
        self.binding = tmp / "binding"
        self.binding.mkdir()
        (self.binding / "probe.py").write_bytes(probe.read_bytes())
        self.out = tmp / "result.json"
        self.control = control

    def write(self, mutation=None, sensitivity=None, expected=None):
        relationship = "exact" if self.control["property"] else "no_mapping"
        probe = {"id": "P-1", "control": self.control["id"], "relationship": relationship,
                 "origin": "reference", "kind": "command", "argv": ["{python}", "aacp_probe.py"],
                 "not_observed_exit": [1], "reference": "probe.py",
                 "description": f"reference probe for {self.control['id']}"}
        mutations = {}
        if mutation:
            probe["mutation"] = "M-1"
            mutations["M-1"] = dict(mutation, file="subject.py")
        if sensitivity:
            probe["sensitivity"] = "W-1"
            mutations["W-1"] = dict(sensitivity, file="subject.py")
        binding = {
            "schema": "aacp-control-binding-v1", "binding_id": "reference", "catalog": CATALOG,
            "assessor": "reference", "subject": {
                "name": "Reference", "version": "0", "repository": "https://example.invalid/reference",
                "revision": self.rev,
                "files": {"subject.py": controls.sha256_bytes((self.dir / "subject.py").read_bytes())}},
            "scope": {"process_model": "single-process", "external_effects": "none",
                      "trust_assumptions": ["reference subject"], "explicit_non_claims": []},
            "runners": {"command": {"install": [{"from": "probe.py", "to": "aacp_probe.py"}]}},
            "mutations": mutations, "probes": [probe]}
        (self.binding / "binding.json").write_text(json.dumps(binding), encoding="utf-8")
        (self.binding / "expected.json").write_text(json.dumps({"probes": expected}), encoding="utf-8")

    def run(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = controls.main(["run", "--binding", str(self.binding), "--subject", str(self.dir),
                                  "--out", str(self.out), "--run-id", "ref"])
        return code, json.loads(self.out.read_text(encoding="utf-8"))

    def clean(self):
        """No pyc, no leftover probe, no modified pin after the run."""
        return subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=self.dir,
                              capture_output=True, text=True).stdout.strip()


class ReferenceSubjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((ROOT / CATALOG).read_text(encoding="utf-8"))
        cls.controls = {c["id"]: c for c in catalog["controls"]}

    def test_every_reference_dir_names_a_catalog_control_and_has_all_parts(self):
        self.assertTrue(REFERENCE_DIRS, "no reference subjects found")
        for d in REFERENCE_DIRS:
            with self.subTest(control=d.name):
                self.assertIn(d.name, self.controls)
                for part in ("weak.py", "probe.py", "repair.json"):
                    self.assertTrue((d / part).is_file(), part)
                weak, protected, repair = load_reference(d)
                self.assertNotEqual(weak, protected, "the repair must change the subject")
                self.assertTrue(repair.get("repair"), "a repair names what it fixes")
                # The inverse edit must be unique in the protected text, or sensitivity cannot be checked.
                self.assertEqual(protected.count(repair["new"]), 1, "inverse anchor is not unique")

    def test_every_control_that_claims_a_reference_subject_has_one(self):
        have = {d.name for d in REFERENCE_DIRS}
        for cid, c in self.controls.items():
            with self.subTest(control=cid):
                if PYTHON_ONLY_ORIGIN in c["origin"]:
                    self.assertIn(cid, have, f"{cid} cites {PYTHON_ONLY_ORIGIN} but has no directory")

    def test_e_f_g_and_cy_controls_are_covered(self):
        """The families added in catalog 1.3.0 each have at least one reference subject."""
        have = {d.name for d in REFERENCE_DIRS}
        for family in ("AACP-E-", "AACP-F-", "AACP-G-", "AACP-CY-"):
            self.assertTrue(any(h.startswith(family) for h in have), family)

    def test_probe_contract_fields_are_substantive(self):
        for cid, c in self.controls.items():
            with self.subTest(control=cid):
                for field, text in c["probe_contract"].items():
                    self.assertTrue(text.strip(), field)
                    if PYTHON_ONLY_ORIGIN in c["origin"]:
                        self.assertGreater(len(text.split()), 6, f"{field} is too thin to implement")
                self.assertTrue(c["origin"], "a control records where it came from")
                self.assertTrue(c["question"].endswith("?"))
                if c["property"] is None:
                    self.assertIn(cid.split("-")[1], ("X", "EV", "CY"))

    def test_weak_subject_is_observed_and_repair_discriminates(self):
        for d in REFERENCE_DIRS:
            with self.subTest(control=d.name), tempfile.TemporaryDirectory() as tmp:
                weak, _, repair = load_reference(d)
                s = Subject(pathlib.Path(tmp), self.controls[d.name], weak, d / "probe.py")
                s.write(mutation=repair, expected={"P-1": {"result": "OBSERVED", "discrimination": "DISCRIMINATES"}})
                code, r = s.run()
                self.assertEqual(code, 0, r["probes"]["P-1"])
                self.assertEqual(r["verdict"], "EXPECTATIONS_MET")
                self.assertEqual(s.clean(), "", "subject left dirty after the run")

    def test_protected_subject_is_not_observed_and_probe_is_sensitive(self):
        for d in REFERENCE_DIRS:
            with self.subTest(control=d.name), tempfile.TemporaryDirectory() as tmp:
                _, protected, repair = load_reference(d)
                weakening = {"repair": "undo: " + repair["repair"], "old": repair["new"], "new": repair["old"]}
                s = Subject(pathlib.Path(tmp), self.controls[d.name], protected, d / "probe.py")
                s.write(sensitivity=weakening, expected={"P-1": {"result": "NOT_OBSERVED",
                                                                  "discrimination": "NOT_RUN",
                                                                  "sensitivity": "SENSITIVE"}})
                code, r = s.run()
                self.assertEqual(code, 0, r["probes"]["P-1"])
                self.assertEqual(s.clean(), "")

    def test_broken_subject_is_a_harness_error_not_a_protection(self):
        """A probe that cannot reach the code must say so (exit 3), never report NOT_OBSERVED."""
        for d in REFERENCE_DIRS:
            with self.subTest(control=d.name), tempfile.TemporaryDirectory() as tmp:
                s = Subject(pathlib.Path(tmp), self.controls[d.name],
                            "raise RuntimeError('subject broken on purpose')\n", d / "probe.py")
                s.write(expected={"P-1": {"result": "NON_VERDICT", "discrimination": "NOT_RUN"}})
                code, r = s.run()
                self.assertEqual(code, 0, r["probes"]["P-1"])
                self.assertEqual(r["probes"]["P-1"]["baseline_exit"], 3)

    def test_probe_rejects_a_subject_whose_legitimate_workflow_is_broken(self):
        """Stubbing every public callable to refuse breaks the legitimate control: exit 3, not 1."""
        for d in REFERENCE_DIRS:
            with self.subTest(control=d.name), tempfile.TemporaryDirectory() as tmp:
                weak, _, _ = load_reference(d)
                refuse_all = weak + '''

def _refuse(*a, **k):
    return "REFUSED"


for _name in list(globals()):
    if not _name.startswith("_") and callable(globals()[_name]) and not isinstance(globals()[_name], type):
        globals()[_name] = _refuse
'''
                s = Subject(pathlib.Path(tmp), self.controls[d.name], refuse_all, d / "probe.py")
                s.write(expected={"P-1": {"result": "NON_VERDICT", "discrimination": "NOT_RUN"}})
                code, r = s.run()
                self.assertEqual(r["probes"]["P-1"]["result"], "NON_VERDICT",
                                 f"exit {r['probes']['P-1'].get('baseline_exit')}: a refuse-everything "
                                 "subject must fail the legitimate control, not look protected")

    def test_report_from_weak_run_fails_exactly_the_controls_property(self):
        for d in REFERENCE_DIRS:
            with self.subTest(control=d.name), tempfile.TemporaryDirectory() as tmp:
                weak, _, repair = load_reference(d)
                control = self.controls[d.name]
                s = Subject(pathlib.Path(tmp), control, weak, d / "probe.py")
                s.write(mutation=repair, expected={"P-1": {"result": "OBSERVED", "discrimination": "DISCRIMINATES"}})
                _, result = s.run()
                _, binding, _, ctl, _ = controls.load_binding(s.binding)
                a = controls.build_assessment(binding, ctl, result, "result.json", "binding")
                validate_assessment(a)
                statuses = {row["id"]: row["status"] for row in a["properties"]}
                self.assertNotIn("PASS", statuses.values())
                if control["property"]:
                    self.assertEqual(statuses[control["property"]], "FAIL")
                    self.assertEqual({p for p, st in statuses.items() if st == "FAIL"}, {control["property"]})
                    row = {r["id"]: r for r in a["properties"]}[control["property"]]
                    self.assertIn(control["normative_basis"]["boundary"], row["caveat"])
                else:
                    self.assertEqual(set(statuses.values()), {"UNTESTED"})
                    self.assertTrue(any(control["id"] in n for n in a["notes"]), "outside-A-G control not noted")

    def test_new_catalog_is_a_strict_superset_of_the_frozen_one(self):
        """1.3.0 adds controls; every 1.2.0 control is byte-for-byte the same object."""
        frozen = json.loads((ROOT / "controls/aacp-controls-v1/catalog.json").read_text(encoding="utf-8"))
        old = {c["id"]: c for c in frozen["controls"]}
        for cid, c in old.items():
            with self.subTest(control=cid):
                self.assertEqual(self.controls.get(cid), c, "a published control changed meaning")
        self.assertGreater(len(self.controls), len(old))
        self.assertEqual([k for k in frozen if k != "controls"],
                         [k for k in json.loads((ROOT / CATALOG).read_text()) if k != "controls"])

    def test_probe_file_convention(self):
        """Probes are self-contained scripts: stdlib only, documented exit codes, legitimate control first."""
        for d in REFERENCE_DIRS:
            with self.subTest(control=d.name):
                src = (d / "probe.py").read_text(encoding="utf-8")
                self.assertIn("Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error", src)
                first_call = re.search(r'harness\(f?"', src)
                self.assertIsNotNone(first_call, "no legitimate-control check")
                self.assertLess(first_call.start(), src.rindex("return "), "legitimate control before the verdict")
                compile(src, str(d / "probe.py"), "exec")
                for forbidden in ("requests", "pytest", "subprocess"):
                    self.assertNotIn(f"import {forbidden}", src)


if __name__ == "__main__":
    unittest.main()
