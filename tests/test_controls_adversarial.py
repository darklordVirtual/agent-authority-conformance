"""Adversarial tests of conformance.controls: can a binding, a probe or a subject obtain a
status it has not earned, and is a run reproducible byte for byte apart from its clock?

Each test names the party that would benefit (an assessor wanting a FAIL, an
implementer wanting an UNTESTED that reads like a PASS, or a sloppy probe) and
checks that the runner refuses or records the attempt rather than counting it.
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
from conformance.validation import validate_assessment
from tests.test_controls import (NOOP, PROBE_SRC, PROTECTED_SRC, REPAIR, SUBJECT_SRC, WEAKEN,
                                 Fixture, command_probe, git, sha)

OBSERVED = {"result": "OBSERVED", "discrimination": "DISCRIMINATES"}
NOT_OBSERVED = {"result": "NOT_OBSERVED", "discrimination": "NOT_RUN"}


def commit(fx, src):
    (fx.subject / "authz.py").write_text(src)
    git(fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "variant")
    fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=fx.subject,
                            capture_output=True, text=True).stdout.strip()


def rows(fx):
    binding_dir, binding, _, ctl, _ = controls.load_binding(fx.binding)
    a = controls.build_assessment(binding, ctl, json.loads(fx.out.read_text()), "r", "b")
    validate_assessment(a)
    return {row["id"]: row for row in a["properties"]}, a


class AssessorCannotManufactureFail(unittest.TestCase):
    """An assessor who wants a FAIL cannot get one from a probe that does not test the weakness."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_probe_that_rewrites_the_subject_cannot_discriminate(self):
        """A probe that plants the weakness itself observes it on the repaired subject too."""
        (self.fx.subject / "tamper.py").write_text(
            "import pathlib, subprocess, sys\n"
            "pathlib.Path('authz.py').write_text(%r)\n"
            "sys.exit(subprocess.call([sys.executable, 'probe_b01.py']))\n" % SUBJECT_SRC)
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "tamper")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()
        self.fx.write([command_probe(argv=["{python}", "tamper.py"])], {"M-1": REPAIR})
        code, r = self.fx.run()
        self.assertEqual(r["probes"]["P-1"]["result"], "OBSERVED")
        self.assertEqual(r["probes"]["P-1"]["discrimination"], "DOES_NOT_DISCRIMINATE")
        self.assertEqual(code, 1)
        self.assertEqual(sha(self.fx.subject / "authz.py"), controls.sha256_bytes(SUBJECT_SRC.encode()),
                         "the pristine bytes are restored even after a tampering probe")
        self.assertEqual(rows(self.fx)[0]["B"]["status"], "UNTESTED")

    def test_repair_that_breaks_the_probe_is_probe_error_not_discrimination(self):
        """A 'repair' that makes the module unimportable crashes the probe; that is not a repaired weakness.

        The probe follows the reference convention (exit 3 on a harness error), which
        is what lets the runner tell a crash from a refusal.
        """
        (self.fx.subject / "probe_conv.py").write_text(
            "import sys\nsys.path.insert(0, '.')\n"
            "try:\n    import authz\nexcept Exception:\n    sys.exit(3)\n"
            "sys.exit(0 if authz.authorize({'actor': 'admin', 'capability': 'pay'}) else 1)\n")
        broken = dict(REPAIR, new="    return (\n")
        self.fx.write([command_probe(argv=["{python}", "probe_conv.py"], not_observed_exit=[1])], {"M-1": broken})
        _, r = self.fx.run()
        self.assertEqual(r["probes"]["P-1"]["discrimination"], "PROBE_ERROR")
        self.assertEqual(rows(self.fx)[0]["B"]["status"], "UNTESTED")

    def test_plain_script_crash_under_repair_reads_as_discrimination(self):
        """A plain script that raises exits 1, the same code a refusal gives, so a crash under
        the repair reads as 'no longer observed' even with `not_observed_exit: [1]`.

        The runner cannot tell the two apart from the exit code alone. This pins the
        behaviour so a reviewer sees why probes must exit 3 (or any code outside
        `not_observed_exit`) on a harness error, as the reference probes do.
        """
        broken = dict(REPAIR, new="    return (\n")
        self.fx.write([command_probe(not_observed_exit=[1])], {"M-1": broken})
        _, r = self.fx.run()
        self.assertEqual(r["probes"]["P-1"]["mutated_exit"], 1)
        self.assertEqual(r["probes"]["P-1"]["discrimination"], "DISCRIMINATES")

    def test_repair_edit_must_target_a_pinned_file(self):
        """Repairing a file the binding did not pin is a run-level NON_VERDICT, not a FAIL."""
        (self.fx.subject / "other.py").write_text("x = 1\n")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "other")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()
        self.fx.write([command_probe()], {"M-1": dict(REPAIR, file="other.py", old="x = 1", new="x = 2")})
        _, r = self.fx.run()
        self.assertEqual(r["verdict"], "NON_VERDICT")
        self.assertIn("unpinned file", r["non_verdict_errors"][0])
        with self.assertRaises(controls.NonVerdict):
            rows(self.fx)

    def test_relationship_downgrades_are_never_counted(self):
        for relationship in ("structural", "partial", "false_analog"):
            with self.subTest(relationship=relationship):
                self.fx.write([command_probe(relationship=relationship)], {"M-1": REPAIR})
                self.fx.run()
                r, _ = rows(self.fx)
                self.assertEqual(r["B"]["status"], "UNTESTED")
                self.assertIn(relationship, r["B"]["reasoning"])

    def test_outside_ag_control_never_produces_a_fail_row(self):
        probe = command_probe(control="AACP-X-01", relationship="no_mapping", argv=["{python}", "probe_b01.py"])
        self.fx.write([probe], {"M-1": REPAIR})
        self.fx.run()
        r, a = rows(self.fx)
        self.assertEqual({row["status"] for row in r.values()}, {"UNTESTED"})
        self.assertTrue(any("AACP-X-01" in n and "OBSERVED, DISCRIMINATES" in n for n in a["notes"]))

    def test_one_weakness_does_not_fail_a_neighbouring_property(self):
        """B-01 observed: only B fails, even though the same code bears on A and C."""
        self.fx.write([command_probe()], {"M-1": REPAIR})
        self.fx.run()
        r, _ = rows(self.fx)
        self.assertEqual([p for p, row in r.items() if row["status"] == "FAIL"], ["B"])

    def test_static_evidence_alone_is_never_fail_even_with_executable_elsewhere(self):
        """A static probe for A next to an executable probe for B does not borrow B's FAIL."""
        static = {"id": "S-A", "control": "AACP-A-03", "relationship": "exact", "origin": "test",
                  "kind": "source-check", "description": "x",
                  "predicates": [{"op": "json_exists", "file": "manifest.json", "path": "key_url"}]}
        self.fx.write([command_probe(), static], {"M-1": REPAIR},
                      expected={"P-1": OBSERVED, "S-A": {"result": "OBSERVED", "discrimination": "NOT_RUN"}})
        self.fx.run()
        r, _ = rows(self.fx)
        self.assertEqual(r["B"]["status"], "FAIL")
        self.assertEqual(r["A"]["status"], "UNTESTED")
        self.assertIn("static source check only", r["A"]["reasoning"])


class ImplementerCannotEarnPass(unittest.TestCase):
    """Nothing an implementer can do to a subject turns a row into PASS."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_protected_subject_without_sensitivity_is_untested_and_says_so(self):
        commit(self.fx, PROTECTED_SRC)
        self.fx.write([command_probe(mutation=None)], {}, expected={"P-1": NOT_OBSERVED})
        self.fx.run()
        r, _ = rows(self.fx)
        self.assertEqual(r["B"]["status"], "UNTESTED")
        self.assertIn("not a PASS", r["B"]["reasoning"])
        self.assertIn("never yield PASS", r["B"]["caveat"])

    def test_subject_that_detects_the_probe_cannot_be_shown_sensitive(self):
        """A subject that refuses only when the probe's marker is present looks protected
        but the weakening does nothing: INSENSITIVE, and the report says the result says nothing."""
        evasive = SUBJECT_SRC.replace(
            '    return request["capability"]',
            '    import sys\n    if any("probe" in a for a in sys.argv):\n        return False\n'
            '    return request["capability"]')
        commit(self.fx, evasive)
        self.fx.write([command_probe(mutation=None, sensitivity="W-1")], {"W-1": WEAKEN},
                      expected={"P-1": dict(NOT_OBSERVED, sensitivity="ANCHOR_ERROR")})
        _, r = self.fx.run()
        # WEAKEN's anchor is the signature check, which this subject never had: the binding is
        # told it cannot show sensitivity for this subject, instead of silently passing.
        self.assertEqual(r["probes"]["P-1"]["sensitivity"], "ANCHOR_ERROR")
        self.assertEqual(rows(self.fx)[0]["B"]["status"], "UNTESTED")

    def test_out_of_scope_needs_an_implementer_statement_and_is_not_credit(self):
        self.fx.write([command_probe()], {"M-1": REPAIR}, out_of_scope_properties={"B": "B is not claimed"})
        self.fx.run()
        r, _ = rows(self.fx)
        self.assertEqual(r["B"]["status"], "OUT_OF_SCOPE")
        self.assertIn("not negative credit", r["B"]["caveat"])

    def test_not_applicable_needs_a_reason(self):
        self.fx.write([command_probe()], {"M-1": REPAIR}, not_applicable=[{"control": "AACP-X-02", "reason": ""}])
        with self.assertRaises(controls.BindingError):
            controls.load_binding(self.fx.binding)

    def test_claimed_status_is_recorded_not_believed(self):
        self.fx.write([command_probe()], {"M-1": REPAIR}, claimed_status="PASS (self-assessed)")
        self.fx.run()
        r, _ = rows(self.fx)
        self.assertEqual(r["B"]["status"], "FAIL")
        self.assertEqual(r["B"]["claimed_status"], "PASS (self-assessed)")


class ExpectationsAreWrittenBeforeTheRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_expectation_for_a_probe_the_binding_lacks_is_a_mismatch(self):
        self.fx.write([command_probe()], {"M-1": REPAIR}, expected={"P-1": OBSERVED, "P-9": OBSERVED})
        code, r = self.fx.run()
        self.assertEqual(code, 1)
        self.assertEqual(r["expectations"]["mismatches"]["P-9"]["observed"], "MISSING")

    def test_probe_without_an_expectation_is_a_mismatch(self):
        self.fx.write([command_probe()], {"M-1": REPAIR}, expected={})
        code, r = self.fx.run()
        self.assertEqual(code, 1)
        self.assertEqual(r["expectations"]["mismatches"]["P-1"]["expected"], "MISSING")

    def test_expectation_must_state_result_and_discrimination(self):
        """An expectation that names only the keys it likes is not an expectation."""
        self.fx.write([command_probe()], {"M-1": REPAIR}, expected={"P-1": {"result": "OBSERVED"}})
        code, r = self.fx.run()
        self.assertEqual(code, 1)
        self.assertIn("P-1", r["expectations"]["mismatches"])

    def test_expected_json_edited_during_the_run_has_no_effect(self):
        """The runner reads expected.json once, before any probe runs."""
        (self.fx.subject / "edit_expected.py").write_text(
            "import json, pathlib, sys\n"
            "p = pathlib.Path(sys.argv[1]); d = json.loads(p.read_text())\n"
            "d['probes']['P-1'] = {'result': 'NOT_OBSERVED', 'discrimination': 'NOT_RUN'}\n"
            "p.write_text(json.dumps(d))\n"
            "sys.exit(1)\n")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "edit")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()
        self.fx.write([command_probe(mutation=None, argv=["{python}", "edit_expected.py",
                                                          str(self.fx.binding / "expected.json")])], {},
                      expected={"P-1": OBSERVED})
        code, r = self.fx.run()
        self.assertEqual(code, 1, "the pre-run expectation (OBSERVED) is what the result is compared to")
        self.assertEqual(r["probes"]["P-1"]["result"], "NOT_OBSERVED")


class ProbeExitConventions(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def exit_with(self, code, not_observed_exit):
        (self.fx.subject / "exit.py").write_text(f"raise SystemExit({code})\n")
        kw = {} if not_observed_exit is None else {"not_observed_exit": not_observed_exit}
        self.fx.write([command_probe(mutation=None, argv=["{python}", "exit.py"], **kw)], {},
                      expected={"P-1": {"result": None, "discrimination": None}})
        _, r = self.fx.run()
        return r["probes"]["P-1"]["result"]

    def test_exit_code_table(self):
        cases = [(0, [1], "OBSERVED"), (1, [1], "NOT_OBSERVED"), (2, [1], "NON_VERDICT"), (3, [1], "NON_VERDICT"),
                 (5, [1, 5], "NOT_OBSERVED"), (0, None, "OBSERVED"), (1, None, "NOT_OBSERVED"),
                 (3, None, "NOT_OBSERVED"), (0, [], "OBSERVED"), (1, [], "NON_VERDICT")]
        for code, allowed, want in cases:
            with self.subTest(exit=code, not_observed_exit=allowed):
                self.assertEqual(self.exit_with(code, allowed), want)

    def test_probe_cannot_see_bytecode_from_the_other_variant(self):
        """A stale .pyc for the repaired module must never serve the pristine run or vice versa."""
        self.fx.write([command_probe(not_observed_exit=[1])], {"M-1": REPAIR})
        code, r = self.fx.run()
        self.assertEqual(code, 0, r)
        self.assertFalse((self.fx.subject / "__pycache__").exists(), "the runner leaves no bytecode cache")
        status = subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=self.fx.subject,
                                capture_output=True, text=True).stdout
        self.assertEqual(status.strip(), "", "subject checkout is clean after the run")

    def test_probe_cwd_is_relative_to_subject(self):
        (self.fx.subject / "sub").mkdir()
        (self.fx.subject / "sub" / "here.py").write_text("import os, sys; sys.exit(0 if os.path.basename(os.getcwd()) == 'sub' else 1)\n")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "sub")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()
        self.fx.write([command_probe(mutation=None, argv=["{python}", "here.py"], cwd="sub")], {},
                      expected={"P-1": {"result": "OBSERVED", "discrimination": "NOT_RUN"}})
        code, _ = self.fx.run()
        self.assertEqual(code, 0)


class RunsAreReproducible(unittest.TestCase):
    """Two runs of the same binding on the same checkout agree on everything but the clock."""

    VOLATILE = {"run_id", "operator", "independence", "started_at_utc", "finished_at_utc"}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def stable(self, record):
        return {k: v for k, v in record.items() if k not in self.VOLATILE}

    def test_identical_findings_and_procedure_digests(self):
        probes = [command_probe(not_observed_exit=[1]),
                  {"id": "S-1", "control": "AACP-B-01", "relationship": "exact", "origin": "test",
                   "kind": "source-check", "mutation": "M-1", "description": "x",
                   "predicates": [{"op": "not_matches", "file": "authz.py", "pattern": "signature"}]}]
        self.fx.write(probes, {"M-1": REPAIR},
                      expected={"P-1": OBSERVED, "S-1": OBSERVED})
        _, first = self.fx.run()
        _, second = self.fx.run()
        self.assertEqual(self.stable(first), self.stable(second))
        self.assertEqual(first["procedure"]["catalog_sha256"], second["procedure"]["catalog_sha256"])
        self.assertEqual(first["procedure"]["binding_sha256"], second["procedure"]["binding_sha256"])

    def test_compare_reports_exactly_the_changed_probe(self):
        self.fx.write([command_probe(not_observed_exit=[1])], {"M-1": REPAIR})
        _, a = self.fx.run()
        a_path = pathlib.Path(self._tmp.name) / "a.json"
        a_path.write_text(json.dumps(a))
        self.fx.write([command_probe(not_observed_exit=[1])], {"M-1": NOOP})
        _, b = self.fx.run()
        b_path = pathlib.Path(self._tmp.name) / "b.json"
        b_path.write_text(json.dumps(b))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            same = controls.main(["compare", str(a_path), str(a_path)])
            diff = controls.main(["compare", str(a_path), str(b_path)])
        self.assertEqual((same, diff), (0, 1))
        text = out.getvalue()
        self.assertIn('"same_findings": true', text)
        self.assertIn('"same_findings": false', text)
        self.assertIn('"P-1"', text)
        self.assertIn("DOES_NOT_DISCRIMINATE", text)

    def test_compare_distinguishes_subjects_with_identical_findings(self):
        self.fx.write([command_probe(not_observed_exit=[1])], {"M-1": REPAIR})
        _, a = self.fx.run()
        b = json.loads(json.dumps(a))
        b["subject"]["revision"] = "e" * 40
        pa, pb = (pathlib.Path(self._tmp.name) / n for n in ("a.json", "b.json"))
        pa.write_text(json.dumps(a))
        pb.write_text(json.dumps(b))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(controls.main(["compare", str(pa), str(pb)]), 1)

    def test_report_markdown_is_identical_across_operators(self):
        self.fx.write([command_probe(not_observed_exit=[1])], {"M-1": REPAIR})
        _, a = self.fx.run()
        b = dict(a, run_id="other", operator="someone else", independence="REPRODUCTION",
                 started_at_utc="2099-01-01T00:00:00Z", finished_at_utc="2099-01-01T00:00:01Z")
        _, binding, _, ctl, _ = controls.load_binding(self.fx.binding)
        md_a = controls.build_markdown(binding, ctl, a, controls.build_assessment(binding, ctl, a, "r", "b"), "b", "r")
        md_b = controls.build_markdown(binding, ctl, b, controls.build_assessment(binding, ctl, b, "r", "b"), "b", "r")
        self.assertEqual(controls.strip_md(md_a), controls.strip_md(md_b))
        self.assertNotEqual(md_a, md_b, "the run line itself still names the operator and independence")


class SourceCheckEdges(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def static(self, predicates, expected_result, control="AACP-B-01", relationship="exact"):
        probe = {"id": "S-1", "control": control, "relationship": relationship, "origin": "test",
                 "kind": "source-check", "description": "x", "predicates": predicates}
        self.fx.write([probe], {}, expected={"S-1": {"result": expected_result, "discrimination": "NOT_RUN"}})
        code, r = self.fx.run()
        return code, r["probes"]["S-1"]

    def test_missing_file_is_non_verdict_not_a_pass(self):
        code, e = self.static([{"op": "not_matches", "file": "nope.py", "pattern": "x"}], "NON_VERDICT")
        self.assertEqual(e["result"], "NON_VERDICT")
        self.assertIn("file not found", e["detail"])

    def test_predicates_are_conjunctive(self):
        code, e = self.static([{"op": "matches", "file": "authz.py", "pattern": "GRANTS"},
                               {"op": "matches", "file": "authz.py", "pattern": "signature"}], "NOT_OBSERVED")
        self.assertEqual(code, 0)
        self.assertEqual([p["holds"] for p in e["predicates"]], [True, False])

    def test_region_end_is_searched_after_start(self):
        (self.fx.subject / "authz.py").write_text("# A\nsignature\n# B\n# A\n# B\n")
        git(self.fx.subject, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "regions")
        self.fx.rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.fx.subject,
                                     capture_output=True, text=True).stdout.strip()
        code, e = self.static([{"op": "matches", "file": "authz.py", "region": {"start": "# A", "end": "# B"},
                                "pattern": "signature"}], "OBSERVED")
        self.assertEqual(e["result"], "OBSERVED")
        self.assertEqual(e["predicates"][0]["detail"], "line 2")

    def test_json_lacks_treats_missing_path_as_lacking(self):
        _, e = self.static([{"op": "json_lacks", "file": "manifest.json", "path": "absent[].x", "value": "y"}],
                           "OBSERVED")
        self.assertEqual(e["result"], "OBSERVED")
        self.assertEqual(e["predicates"][0]["detail"], "path absent")

    def test_json_equals_against_digest_of_literal(self):
        _, e = self.static([{"op": "json_equals", "file": "manifest.json", "path": "digest",
                             "value_sha256_of": "finished=True\nerror_lines=1\n"}], "NOT_OBSERVED")
        self.assertEqual(e["result"], "NOT_OBSERVED")

    @unittest.expectedFailure
    def test_malformed_json_is_a_probe_non_verdict_not_a_crash(self):
        """GAP: a JSON predicate over a file that is not JSON raises out of the run.

        Expected: the probe is NON_VERDICT with a detail, like a missing file or
        region, and the other probes still run. Today the whole run aborts with a
        traceback and no result record is written. Runner change needed in
        eval_predicate (catch json.JSONDecodeError -> NonVerdict).
        """
        _, e = self.static([{"op": "json_exists", "file": "authz.py", "path": "x"}], "NON_VERDICT")
        self.assertEqual(e["result"], "NON_VERDICT")
        self.assertIn("JSON", e["detail"])

    def unknown_op_run(self, path):
        probe = {"id": "S-1", "control": "AACP-B-01", "relationship": "exact", "origin": "test",
                 "kind": "source-check", "description": "x",
                 "predicates": [{"op": "contains", "file": "manifest.json", "path": path}]}
        self.fx.write([probe], {}, expected={"S-1": {"result": None, "discrimination": None}})
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return controls.main(["run", "--binding", str(self.fx.binding), "--subject", str(self.fx.subject),
                                  "--out", str(self.fx.out), "--run-id", "t"])

    def test_unknown_predicate_op_on_a_present_path_is_a_binding_error(self):
        self.assertEqual(self.unknown_op_run("digest"), 2)

    @unittest.expectedFailure
    def test_unknown_predicate_op_is_rejected_when_the_binding_loads(self):
        """GAP: predicate ops are only checked when evaluated, after the path lookup.

        An unknown op over an absent path is read as NOT_OBSERVED ('path absent')
        and the run completes. Expected: load_binding rejects an unknown op, so a
        typo in a binding is a BindingError (exit 2) before anything runs.
        """
        self.assertEqual(self.unknown_op_run("absent"), 2)


class BindingShape(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(pathlib.Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_duplicate_probe_id_is_rejected(self):
        self.fx.write([command_probe(), command_probe()], {"M-1": REPAIR})
        with self.assertRaises(controls.BindingError):
            controls.load_binding(self.fx.binding)

    def test_unknown_sensitivity_reference_is_rejected(self):
        self.fx.write([command_probe(mutation=None, sensitivity="W-404")], {})
        with self.assertRaises(controls.BindingError):
            controls.load_binding(self.fx.binding)

    def test_unknown_probe_kind_is_rejected(self):
        self.fx.write([command_probe(kind="shell", mutation=None)], {})
        with self.assertRaises(controls.BindingError):
            controls.load_binding(self.fx.binding)

    def test_sensitivity_not_run_when_weakness_already_observed(self):
        self.fx.write([command_probe(sensitivity="W-1")], {"M-1": REPAIR, "W-1": WEAKEN},
                      expected={"P-1": dict(OBSERVED, sensitivity="NOT_RUN")})
        code, r = self.fx.run()
        self.assertEqual(code, 0, r["probes"]["P-1"])

    def test_discrimination_not_run_when_weakness_not_observed(self):
        commit(self.fx, PROTECTED_SRC)
        self.fx.write([command_probe()], {"M-1": REPAIR}, expected={"P-1": NOT_OBSERVED})
        code, r = self.fx.run()
        self.assertEqual(code, 0, r["probes"]["P-1"])
        self.assertEqual(r["probes"]["P-1"]["discrimination"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
