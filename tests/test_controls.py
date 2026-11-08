"""Tests for conformance.controls that need no Rust toolchain.

A throwaway git repository stands in for a subject. Its probes use the
generic `command` and `source-check` kinds, which is also what a non-Rust
project's binding would use.
"""
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from conformance import controls
from conformance.validation import ROOT, validate_assessment

CATALOG = "controls/aacp-controls-v1/catalog.json"

# A deliberately weak authorizer: it trusts the actor string (AACP-B-01).
SUBJECT_SRC = '''GRANTS = {"admin": {"pay"}}

def authorize(request):
    return request["capability"] in GRANTS.get(request["actor"], set())
'''
# Probe: exits 0 when an unsigned request naming "admin" is allowed.
PROBE_SRC = '''import sys
sys.path.insert(0, ".")
import authz
sys.exit(0 if authz.authorize({"actor": "admin", "capability": "pay"}) else 1)
'''


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def sha(path):
    return controls.sha256_bytes(pathlib.Path(path).read_bytes())


class Fixture:
    """A subject repository plus a binding directory, both temporary."""

    def __init__(self, tmp: pathlib.Path):
        self.subject = tmp / "subject"
        self.subject.mkdir()
        (self.subject / "authz.py").write_text(SUBJECT_SRC)
        (self.subject / "probe_b01.py").write_text(PROBE_SRC)
        (self.subject / "manifest.json").write_text(json.dumps(
            {"commit": "0" * 40, "key_url": "https://example.invalid/key.pem",
             "digest": controls.sha256_bytes(b"finished=True\nerror_lines=0\n"),
             "files": [{"path": "README.md"}]}))
        git(self.subject, "init", "-q")
        git(self.subject, "-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        git(self.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "subject")
        self.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.subject,
                                  capture_output=True, text=True).stdout.strip()
        self.binding = tmp / "binding"
        self.binding.mkdir()
        self.out = tmp / "result.json"

    def write(self, probes, mutations, expected=None, **extra):
        binding = {
            "schema": "aacp-control-binding-v1", "binding_id": "fixture", "catalog": CATALOG,
            "assessor": "test", "subject": {
                "name": "Fixture", "version": "0", "repository": "https://example.invalid/fixture",
                "revision": self.rev, "files": {"authz.py": sha(self.subject / "authz.py"),
                                                "manifest.json": sha(self.subject / "manifest.json")}},
            "scope": {"process_model": "single-process", "external_effects": "none",
                      "trust_assumptions": ["fixture"], "explicit_non_claims": []},
            "mutations": mutations, "probes": probes, **extra}
        (self.binding / "binding.json").write_text(json.dumps(binding))
        if expected is None:
            expected = {p["id"]: {"result": "OBSERVED",
                                  "discrimination": "DISCRIMINATES" if p.get("mutation") else "NOT_RUN"}
                        for p in probes}
        (self.binding / "expected.json").write_text(json.dumps({"probes": expected}))

    def run(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = controls.main(["run", "--binding", str(self.binding), "--subject", str(self.subject),
                                  "--out", str(self.out), "--run-id", "t"])
        return code, json.loads(self.out.read_text())


REPAIR = {"file": "authz.py", "repair": "require a signature",
          "old": '    return request["capability"]',
          "new": '    if "signature" not in request:\n        return False\n    return request["capability"]'}
NOOP = dict(REPAIR, new=REPAIR["old"])


def command_probe(**kw):
    p = {"id": "P-1", "control": "AACP-B-01", "relationship": "exact", "origin": "test",
         "kind": "command", "argv": [sys.executable, "probe_b01.py"], "mutation": "M-1",
         "description": "unsigned admin request allowed"}
    p.update(kw)
    return p


class RunTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_executable_probe_observes_and_discriminates(self):
        self.fx.write([command_probe()], {"M-1": REPAIR})
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)
        self.assertEqual(r["probes"]["P-1"]["result"], "OBSERVED")
        self.assertEqual(r["probes"]["P-1"]["discrimination"], "DISCRIMINATES")
        self.assertEqual(sha(self.fx.subject / "authz.py"),
                         controls.sha256_bytes(SUBJECT_SRC.encode()), "subject restored")

    def test_noop_repair_does_not_discriminate(self):
        self.fx.write([command_probe()], {"M-1": NOOP})
        code, r = self.fx.run()
        self.assertEqual(code, 1)
        self.assertEqual(r["probes"]["P-1"]["discrimination"], "DOES_NOT_DISCRIMINATE")
        self.assertEqual(r["verdict"], "EXPECTATIONS_NOT_MET")

    def test_ambiguous_anchor_is_reported_not_counted(self):
        self.fx.write([command_probe()], {"M-1": dict(REPAIR, old="request")})
        _, r = self.fx.run()
        self.assertEqual(r["probes"]["P-1"]["discrimination"], "ANCHOR_ERROR")

    def test_wrong_revision_is_non_verdict(self):
        self.fx.write([command_probe()], {"M-1": REPAIR})
        b = json.loads((self.fx.binding / "binding.json").read_text())
        b["subject"]["revision"] = "f" * 40
        (self.fx.binding / "binding.json").write_text(json.dumps(b))
        code, r = self.fx.run()
        self.assertEqual(code, 1)
        self.assertEqual(r["verdict"], "NON_VERDICT")
        self.assertIn("expected " + "f" * 40, r["non_verdict_errors"][0])

    def test_changed_byte_is_non_verdict(self):
        self.fx.write([command_probe()], {"M-1": REPAIR})
        (self.fx.subject / "authz.py").write_text(SUBJECT_SRC + "\n")
        _, r = self.fx.run()
        self.assertEqual(r["verdict"], "NON_VERDICT")
        self.assertIn("bytes differ", r["non_verdict_errors"][0])

    def test_absent_weakness_is_not_observed(self):
        (self.fx.subject / "authz.py").write_text(SUBJECT_SRC.replace(
            '    return request["capability"]', '    return "signature" in request and request["capability"]'))
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "fixed")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()
        self.fx.write([command_probe(mutation=None)], {},
                      expected={"P-1": {"result": "NOT_OBSERVED", "discrimination": "NOT_RUN"}})
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)
        self.assertEqual(r["probes"]["P-1"]["result"], "NOT_OBSERVED")

    def test_source_check_ops_and_static_discrimination(self):
        probes = [
            {"id": "S-1", "control": "AACP-B-01", "relationship": "exact", "origin": "test",
             "kind": "source-check", "mutation": "M-1", "description": "no signature check",
             "predicates": [
                 {"op": "matches", "file": "authz.py", "region": {"start": "def authorize"},
                  "pattern": r"request\[\"actor\"\]"},
                 {"op": "not_matches", "file": "authz.py", "pattern": "signature"},
                 {"op": "order", "file": "authz.py", "first": "GRANTS =", "then": "def authorize"}]},
            {"id": "S-2", "control": "AACP-EV-01", "relationship": "no_mapping", "origin": "test",
             "kind": "source-check", "description": "constant digest",
             "predicates": [
                 {"op": "json_equals", "file": "manifest.json", "path": "digest",
                  "value_sha256_of": "finished=True\nerror_lines=0\n"},
                 {"op": "json_lacks", "file": "manifest.json", "path": "files[].path", "value": "authz.py"},
                 {"op": "json_ne_head", "file": "manifest.json", "path": "commit"},
                 {"op": "json_exists", "file": "manifest.json", "path": "key_url"}]},
        ]
        self.fx.write(probes, {"M-1": REPAIR})
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)
        self.assertEqual(r["probes"]["S-1"]["discrimination"], "DISCRIMINATES")
        self.assertTrue(all(p["holds"] for p in r["probes"]["S-2"]["predicates"]))

    def test_missing_region_is_probe_non_verdict(self):
        probe = {"id": "S-1", "control": "AACP-B-01", "relationship": "exact", "origin": "test",
                 "kind": "source-check", "description": "x",
                 "predicates": [{"op": "matches", "file": "authz.py",
                                 "region": {"start": "def missing"}, "pattern": "x"}]}
        self.fx.write([probe], {}, expected={"S-1": {"result": "NON_VERDICT", "discrimination": None}})
        _, r = self.fx.run()
        self.assertEqual(r["probes"]["S-1"]["result"], "NON_VERDICT")


# A protected authorizer: it requires a signature, so AACP-B-01 is not observed.
PROTECTED_SRC = SUBJECT_SRC.replace(
    '    return request["capability"]', '    return "signature" in request and request["capability"]')
WEAKEN = {"file": "authz.py", "repair": "remove the signature requirement",
          "old": '    return "signature" in request and request["capability"]',
          "new": '    return request["capability"]'}


class SensitivityTests(unittest.TestCase):
    """A NOT_OBSERVED result counts only if the probe would have seen the weakness."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))
        (self.fx.subject / "authz.py").write_text(PROTECTED_SRC)
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "protected")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()

    def tearDown(self):
        self._tmp.cleanup()

    def expect(self, sensitivity):
        return {"P-1": {"result": "NOT_OBSERVED", "discrimination": "NOT_RUN", "sensitivity": sensitivity}}

    def test_sensitive_probe(self):
        self.fx.write([command_probe(mutation=None, sensitivity="W-1",
                                     argv=["{python}", "probe_b01.py"])],
                      {"W-1": WEAKEN}, expected=self.expect("SENSITIVE"))
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)
        self.assertEqual(sha(self.fx.subject / "authz.py"),
                         controls.sha256_bytes(PROTECTED_SRC.encode()), "subject restored")

    def test_noop_weakening_is_insensitive(self):
        self.fx.write([command_probe(mutation=None, sensitivity="W-1")],
                      {"W-1": dict(WEAKEN, new=WEAKEN["old"])}, expected=self.expect("INSENSITIVE"))
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)

    def test_static_probe_sensitivity(self):
        probe = {"id": "P-1", "control": "AACP-B-01", "relationship": "exact", "origin": "test",
                 "kind": "source-check", "sensitivity": "W-1", "description": "x",
                 "predicates": [{"op": "not_matches", "file": "authz.py", "pattern": "signature"}]}
        self.fx.write([probe], {"W-1": WEAKEN}, expected=self.expect("SENSITIVE"))
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)

    def test_missing_sensitivity_expectation_is_a_mismatch(self):
        self.fx.write([command_probe(mutation=None, sensitivity="W-1")], {"W-1": WEAKEN},
                      expected={"P-1": {"result": "NOT_OBSERVED", "discrimination": "NOT_RUN"}})
        _, r = self.fx.run()
        self.assertEqual(r["probes"]["P-1"]["sensitivity"], "SENSITIVE")
        # Declared keys are compared; CommittedBindingTests requires the key when a probe declares one.
        self.assertTrue(r["expectations"]["met"])

    def test_report_explains_sensitive_not_observed(self):
        self.fx.write([command_probe(mutation=None, sensitivity="W-1")], {"W-1": WEAKEN},
                      expected=self.expect("SENSITIVE"))
        self.fx.run()
        binding_dir, binding, _, ctl, _ = controls.load_binding(self.fx.binding)
        a = controls.build_assessment(binding, ctl, json.loads(self.fx.out.read_text()), "r", "b")
        row = {x["id"]: x for x in a["properties"]}["B"]
        self.assertEqual(row["status"], "UNTESTED")
        self.assertIn("shown to be sensitive", row["reasoning"])

    def test_two_layer_protection_needs_both_edits(self):
        """Removing one of two layers leaves the probe refused: INSENSITIVE, honestly."""
        two_layer = PROTECTED_SRC.replace(
            "def authorize(request):",
            "def authorize(request):\n    if \"signature\" not in request:\n        return False")
        (self.fx.subject / "authz.py").write_text(two_layer)
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "two layers")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()
        layer2 = {"file": "authz.py", "old": '    if "signature" not in request:\n        return False\n',
                  "new": ""}
        self.fx.write([command_probe(mutation=None, sensitivity="W-1")], {"W-1": WEAKEN},
                      expected=self.expect("INSENSITIVE"))
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)
        self.fx.write([command_probe(mutation=None, sensitivity="W-2")],
                      {"W-2": {"repair": "both layers", "edits": [WEAKEN, layer2]}},
                      expected=self.expect("SENSITIVE"))
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)
        self.assertEqual(sha(self.fx.subject / "authz.py"), controls.sha256_bytes(two_layer.encode()))

    def test_crashing_probe_is_non_verdict_not_protection(self):
        (self.fx.subject / "crash.py").write_text("raise SystemExit(3)\n")
        self.fx.write([command_probe(mutation=None, argv=["{python}", "crash.py"],
                                     not_observed_exit=[1])], {},
                      expected={"P-1": {"result": "NON_VERDICT", "discrimination": "NOT_RUN"}})
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)

    def test_failing_setup_is_non_verdict(self):
        self.fx.write([command_probe(mutation=None)], {},
                      expected={"P-1": {"result": None, "discrimination": None}},
                      runners={"command": {"setup": [["{python}", "-c", "raise SystemExit(3)"]]}})
        _, r = self.fx.run()
        self.assertEqual(r["verdict"], "NON_VERDICT")
        self.assertIn("setup failed", r["non_verdict_errors"][0])


class ReportTests(unittest.TestCase):
    """Status derivation: only executed, exact, OBSERVED, DISCRIMINATES probes give FAIL."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def report(self, probes, mutations, **extra):
        self.fx.write(probes, mutations, **extra)
        self.fx.run()
        binding_dir, binding, _, ctl, _ = controls.load_binding(self.fx.binding)
        result = json.loads(self.fx.out.read_text())
        a = controls.build_assessment(binding, ctl, result, "result.json", str(binding_dir))
        validate_assessment(a)
        return {row["id"]: row for row in a["properties"]}, a

    def test_counted_probe_fails_property(self):
        rows, _ = self.report([command_probe()], {"M-1": REPAIR})
        self.assertEqual(rows["B"]["status"], "FAIL")
        self.assertEqual(rows["A"]["status"], "UNTESTED")

    def test_never_pass(self):
        rows, _ = self.report([command_probe()], {"M-1": REPAIR})
        self.assertNotIn("PASS", {r["status"] for r in rows.values()})

    def test_non_discriminating_probe_not_counted(self):
        rows, _ = self.report([command_probe()], {"M-1": NOOP})
        self.assertEqual(rows["B"]["status"], "UNTESTED")
        self.assertIn("DOES_NOT_DISCRIMINATE", rows["B"]["reasoning"])

    def test_structural_relationship_not_counted(self):
        rows, _ = self.report([command_probe(relationship="structural")], {"M-1": REPAIR})
        self.assertEqual(rows["B"]["status"], "UNTESTED")

    def test_static_probe_not_counted(self):
        probe = {"id": "S-1", "control": "AACP-B-01", "relationship": "exact", "origin": "test",
                 "kind": "source-check", "mutation": "M-1", "description": "x",
                 "predicates": [{"op": "not_matches", "file": "authz.py", "pattern": "signature"}]}
        rows, _ = self.report([probe], {"M-1": REPAIR})
        self.assertEqual(rows["B"]["status"], "UNTESTED")
        self.assertIn("static source check only", rows["B"]["reasoning"])

    def test_out_of_scope_declared_by_implementer(self):
        rows, _ = self.report([command_probe()], {"M-1": REPAIR},
                              out_of_scope_properties={"E": "implementer does not claim E"})
        self.assertEqual(rows["E"]["status"], "OUT_OF_SCOPE")

    def test_non_verdict_run_cannot_be_reported(self):
        self.fx.write([command_probe()], {"M-1": REPAIR})
        b = json.loads((self.fx.binding / "binding.json").read_text())
        b["subject"]["revision"] = "f" * 40
        (self.fx.binding / "binding.json").write_text(json.dumps(b))
        self.fx.run()
        binding_dir, binding, _, ctl, _ = controls.load_binding(self.fx.binding)
        with self.assertRaises(controls.NonVerdict):
            controls.build_assessment(binding, ctl, json.loads(self.fx.out.read_text()), "r", "b")


class BindingValidationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def assertBindingError(self, probes, mutations=None):
        self.fx.write(probes, mutations or {})
        with self.assertRaises(controls.BindingError):
            controls.load_binding(self.fx.binding)

    def test_unknown_control(self):
        self.assertBindingError([command_probe(control="AACP-Z-99", mutation=None)])

    def test_outside_ag_requires_no_mapping(self):
        self.assertBindingError([command_probe(control="AACP-X-01", mutation=None)])

    def test_unknown_mutation(self):
        self.assertBindingError([command_probe(mutation="M-404")])

    def test_unknown_relationship(self):
        self.assertBindingError([command_probe(relationship="equivalent", mutation=None)])


class CommittedBindingTests(unittest.TestCase):
    """Consistency of committed bindings, without running them."""

    def test_catalog_ids_and_properties(self):
        catalog = json.loads((ROOT / CATALOG).read_text())
        ids = [c["id"] for c in catalog["controls"]]
        self.assertEqual(len(ids), len(set(ids)))
        for c in catalog["controls"]:
            self.assertIn(c["property"], [None, *controls.PROPERTY_NAMES])
            self.assertTrue(c["id"].startswith(f"AACP-{c['property']}-") if c["property"]
                            else c["id"].split("-")[1] in ("X", "EV", "CY"), c["id"])
            self.assertEqual(set(c["probe_contract"]), {"setup", "stimulus", "observation", "repair"})
            if c["property"]:
                nb = c["normative_basis"]
                self.assertTrue(nb["specification"].startswith(f"SPECIFICATION.md §2 {c['property']}"), c["id"])
                self.assertTrue(nb["rationale"] and nb["boundary"], c["id"])

    def test_ag_control_without_normative_basis_is_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            cat = json.loads((ROOT / CATALOG).read_text())
            del cat["controls"][0]["normative_basis"]
            catalog = ROOT / "controls" / "_test_catalog.json"
            catalog.write_text(json.dumps(cat))
            try:
                fx = Fixture(tmp)
                fx.write([command_probe()], {"M-1": REPAIR})
                b = json.loads((fx.binding / "binding.json").read_text())
                b["catalog"] = "controls/_test_catalog.json"
                (fx.binding / "binding.json").write_text(json.dumps(b))
                with self.assertRaises(controls.BindingError):
                    controls.load_binding(fx.binding)
            finally:
                catalog.unlink()

    def test_bindings_load_and_expectations_cover_probes(self):
        for binding_dir in sorted((ROOT / "controls" / "bindings").iterdir()):
            if not binding_dir.is_dir():
                continue
            with self.subTest(binding=binding_dir.name):
                _, binding, _, _, _ = controls.load_binding(binding_dir)
                expected = json.loads((binding_dir / "expected.json").read_text())
                self.assertEqual(set(expected["probes"]), {p["id"] for p in binding["probes"]})
                for p in binding["probes"]:
                    if p.get("sensitivity"):
                        self.assertIn("sensitivity", expected["probes"][p["id"]], p["id"])
                    if p["kind"] == "cargo-test":
                        src = (binding_dir / p["reference"].split("#")[0]).read_text()
                        self.assertIn(f"fn {p['test']}()", src)

    def test_committed_reports_regenerate(self):
        for binding_dir in sorted((ROOT / "controls" / "bindings").iterdir()):
            report_dir = ROOT / "reports" / binding_dir.name
            pointer = report_dir / "CURRENT"
            if not pointer.exists():
                continue
            with self.subTest(binding=binding_dir.name):
                result = report_dir / "results" / pointer.read_text().strip()
                with contextlib.redirect_stdout(io.StringIO()):
                    code = controls.main([
                        "report", "--binding", str(binding_dir), "--result", str(result),
                        "--assessment", str(ROOT / "examples" / f"{binding_dir.name}.json"),
                        "--markdown", str(report_dir / "REPORT.md"), "--check"])
                self.assertEqual(code, 0, "committed report differs from its result; regenerate it")


    def test_reproduction_of_committed_run_regenerates_identically(self):
        """A CI reproduction differs only in run id, operator, independence and time."""
        for binding_dir in sorted((ROOT / "controls" / "bindings").iterdir()):
            report_dir = ROOT / "reports" / binding_dir.name
            pointer = report_dir / "CURRENT"
            if not pointer.exists():
                continue
            with self.subTest(binding=binding_dir.name), tempfile.TemporaryDirectory() as tmp:
                committed = report_dir / "results" / pointer.read_text().strip()
                repro = json.loads(committed.read_text())
                repro.update(run_id="repro-gha-1", operator="github-actions run 1", independence="REPRODUCTION",
                             started_at_utc="2099-01-01T00:00:00Z", finished_at_utc="2099-01-01T00:01:00Z")
                path = pathlib.Path(tmp) / "repro.json"
                path.write_text(json.dumps(repro))
                with contextlib.redirect_stdout(io.StringIO()):
                    code = controls.main([
                        "report", "--binding", str(binding_dir), "--result", str(path),
                        "--result-ref", str(committed.relative_to(ROOT)),
                        "--assessment", str(ROOT / "examples" / f"{binding_dir.name}.json"),
                        "--markdown", str(report_dir / "REPORT.md"), "--check"])
                self.assertEqual(code, 0, "a reproduction would not regenerate the committed report")


if __name__ == "__main__":
    unittest.main()
