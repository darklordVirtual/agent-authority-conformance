"""Probes, challenge context, bytes inputs and the public-boundary lifecycle."""

import copy
import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from unittest import mock

from aacp.tracks import evidence_record, next_actions
from conformance.lab import consent, lifecycle, runner, state
from conformance.lab.canonical import read_json, sha256_bytes, sha256_json, write_json
from conformance.lab.errors import GateError, ScopeError
from conformance.lab.kinds import verification
from conformance.lab.rerun import compare
from conformance.lab.scope import validate_scope
from tests.lab.helpers import AGREE_REF, FIXTURES, NOW, LabTest, fixture_files

FAKE_GH = Path(__file__).resolve().parent / "fake_gh.py"
ORG = "Runner-Org"

PROBE = {"id": "p1", "text": "The value is bounded.", "class": "BINDING_GAP", "check": "probes:demonstrate",
         "inputs": ["within", "over"], "reads_fields": ["execution.nativeValue"],
         "runner_assessment": {"level": "low", "rationale": "toy"}}
CHALLENGE = {"ref": "https://example.invalid/issues/1#challenge", "by": "producer",
             "asked": ["recompute the values"], "requests_endorsement": True}


def verification_scope():
    return json.loads((FIXTURES / "toy-verification-run" / "SCOPE.json").read_text(encoding="utf-8"))


class ScopeRulesTest(unittest.TestCase):
    def test_valid_probe_challenge_and_format(self):
        s = verification_scope()
        s["probes"] = [dict(PROBE)]
        s["challenge"] = dict(CHALLENGE)
        s["inputs"][0]["format"] = "bytes"
        validate_scope(s)

    def test_rejections(self):
        cases = {
            "bad class": lambda s: s["probes"][0].__setitem__("class", "SEVERE"),
            "unknown input": lambda s: s["probes"][0].__setitem__("inputs", ["nope"]),
            "duplicate input": lambda s: s["probes"][0].__setitem__("inputs", ["within", "within"]),
            "id equals claim": lambda s: s["probes"][0].__setitem__("id", s["claims"][0]["id"]),
            "no assessment": lambda s: s["probes"][0].pop("runner_assessment"),
            "bad level": lambda s: s["probes"][0]["runner_assessment"].__setitem__("level", "critical"),
            "extra assessment key": lambda s: s["probes"][0]["runner_assessment"].__setitem__("score", 3),
            "bad locator lines": lambda s: s["probes"][0].__setitem__(
                "source_locators", [{"subject": 0, "path": "a.json", "lines": "5-2", "note": "n"}]),
            "locator subject": lambda s: s["probes"][0].__setitem__(
                "source_locators", [{"subject": 4, "path": "a.json", "lines": "1", "note": "n"}]),
            "empty probes": lambda s: s.__setitem__("probes", []),
            "bad format": lambda s: s["inputs"][0].__setitem__("format", "yaml"),
            "challenge http": lambda s: s.__setitem__("challenge", {**CHALLENGE, "ref": "http://x"}),
            "challenge no asked": lambda s: s.__setitem__("challenge", {**CHALLENGE, "asked": []}),
            "challenge consent key": lambda s: s.__setitem__("challenge", {**CHALLENGE, "consent": True}),
            "challenge endorsement type": lambda s: s.__setitem__(
                "challenge", {**CHALLENGE, "requests_endorsement": "yes"}),
        }
        for label, edit in cases.items():
            s = verification_scope()
            s["probes"] = [copy.deepcopy(PROBE)]
            edit(s)
            with self.subTest(label), self.assertRaises(ScopeError):
                validate_scope(s)

    def test_probes_are_verification_only(self):
        s = json.loads((FIXTURES / "toy-run" / "SCOPE.json").read_text(encoding="utf-8"))
        s["probes"] = [dict(PROBE)]
        with self.assertRaisesRegex(ScopeError, "only for verification"):
            validate_scope(s)

    def test_locator_must_be_pinned_after_pin(self):
        s = verification_scope()
        s["subjects"][0]["files_sha256"] = {"receipts/within.json": "a" * 64}
        s["probes"] = [{**PROBE, "source_locators": [{"subject": 0, "path": "receipts/over.json", "lines": "1",
                                                      "note": "n"}]}]
        validate_scope(s)
        with self.assertRaisesRegex(ScopeError, "not a pinned file"):
            validate_scope(s, require_pins=True)

    def test_public_boundary_subjects(self):
        s = json.loads((FIXTURES / "toy-offer-run" / "SCOPE.json").read_text(encoding="utf-8"))
        s.pop("offer")
        s["public_boundary"] = {"repo": "https://example.invalid/toy-receipts", "commit": "a" * 40,
                                "path": "README.md", "sha256": "b" * 64, "procedure_ref": "README.md#p",
                                "claims_ref": "README.md#c", "classification_ref": "README.md#k"}
        validate_scope(s)  # one subject, as before
        s["subjects"].append({**s["subjects"][0], "commit": "c" * 40})
        validate_scope(s)  # two revisions of the boundary's own repository
        s["subjects"][1]["repo"] = "https://example.invalid/other-project"
        with self.assertRaisesRegex(ScopeError, "own repository"):
            validate_scope(s)


def _probe_check(out):
    return lambda docs, context: out


class ProbeContractTest(unittest.TestCase):
    def run_probe(self, out, probe=PROBE):
        check = out if callable(out) else _probe_check(out)
        return verification.run_probe(check, probe, {"within": {}}, ["within:sha256:" + "a" * 64], {})

    def good(self, **overrides):
        return {"observation": "DEMONSTRATED", "reads": ["execution.nativeValue"], "witness": {"root": "ab"},
                "affects_pinned_artifact": True, "message": "seen", **overrides}

    def test_completed(self):
        r = self.run_probe(self.good())
        self.assertEqual((r["execution"], r["observation"], r["witness"]), ("COMPLETED", "DEMONSTRATED", {"root": "ab"}))

    def test_contract_errors(self):
        def boom(docs, context):
            raise RuntimeError("x")
        cases = {
            "exception": boom,
            "bad_return": _probe_check([]),
            "bad_observation": self.good(observation="PASS"),
            "undeclared_read": self.good(reads=["secret"]),
            "bad_witness": self.good(witness={"ratio": 0.5}),
            "aggregate_key": self.good(witness={"score": 1}),
            "missing_witness": self.good(witness={}),
            "bad_affects": self.good(affects_pinned_artifact="yes"),
            "missing_message": self.good(message=" "),
            "bad_execution": self.good(execution="DONE"),
        }
        for code, out in cases.items():
            with self.subTest(code):
                r = self.run_probe(out)
                self.assertEqual((r["execution"], r["observation"], r["verifier_error"]["code"]), ("ERROR", None, code))

    def test_not_demonstrated_may_have_empty_witness(self):
        r = self.run_probe(self.good(observation="NOT_DEMONSTRATED", witness={}, affects_pinned_artifact=False))
        self.assertEqual(r["observation"], "NOT_DEMONSTRATED")

    def test_unsupported_is_a_non_verdict(self):
        r = self.run_probe({"execution": "UNSUPPORTED", "message": "no key"})
        self.assertEqual((r["execution"], r["observation"]), ("UNSUPPORTED", None))


class BytesInputTest(LabTest):
    def test_file_and_directory(self):
        base = self.tmp / "tree"
        (base / "d" / "sub").mkdir(parents=True)
        (base / "d" / "a.bin").write_bytes(b"\x00\x01")
        (base / "d" / "sub" / "b.txt").write_bytes(b"text")
        doc, digest = verification.load_input(base / "d" / "a.bin", "bytes")
        self.assertEqual((doc, digest), ({"a.bin": b"\x00\x01"}, sha256_bytes(b"\x00\x01")))
        doc, digest = verification.load_input(base / "d", "bytes")
        self.assertEqual(doc, {"a.bin": b"\x00\x01", "sub/b.txt": b"text"})
        self.assertEqual(digest, sha256_json({"a.bin": sha256_bytes(b"\x00\x01"), "sub/b.txt": sha256_bytes(b"text")}))
        with self.assertRaises(ScopeError):
            verification.load_input(base / "missing.bin", "bytes")


class RerunCompareTest(unittest.TestCase):
    def test_probe_witness_divergence_is_reported(self):
        record = {"probe": "p1", "execution": "COMPLETED", "observation": "DEMONSTRATED", "reads": ["x"],
                  "witness": {"root": "aa"}, "affects_pinned_artifact": True, "evidence": ["i:sha256:" + "a" * 64]}
        changed = {**record, "witness": {"root": "bb"}}
        diffs = compare({"results/probes.json": {"records": [record]}},
                        {"results/probes.json": {"records": [changed]}})
        self.assertEqual([d["item"] for d in diffs], ["probe p1"])


PROBES_PY = '''
def demonstrate(docs, context):
    within, over = docs["within"], docs["over"]
    return {"observation": "DEMONSTRATED", "reads": ["execution.nativeValue"],
            "witness": {"within": within["execution"]["nativeValue"], "over": over["execution"]["nativeValue"]},
            "affects_pinned_artifact": True, "message": "both values read"}
'''


class PublicBoundaryLifecycleTest(LabTest):
    def setUp(self):
        super().setUp()
        self.gh_state = self.tmp / "gh.json"
        self.gh_state.write_text(json.dumps({"owners": {ORG: "Organization"}, "repos": {}, "calls": []}))
        env = {"AAC_GH": f"{shlex.quote(sys.executable)} {shlex.quote(str(FAKE_GH))}",
               "FAKE_GH_STATE": str(self.gh_state), "AAC_GIT_REMOTE_BASE": str(self.tmp / "github")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def shared_run(self):
        import hashlib
        files = fixture_files("toy-receipts")
        files["BOUNDARY.md"] = "# Public boundary\n\nProcedure, claims and classification.\n"
        repo, commit = self.remote_repo("toy-receipts", files)
        scope = json.loads((FIXTURES / "toy-offer-run" / "SCOPE.json").read_text(encoding="utf-8"))
        scope.pop("offer")
        scope["public_boundary"] = {"repo": repo, "commit": commit, "path": "BOUNDARY.md",
                                    "sha256": hashlib.sha256(files["BOUNDARY.md"].encode()).hexdigest(),
                                    "procedure_ref": "BOUNDARY.md#procedure", "claims_ref": "BOUNDARY.md#claims",
                                    "classification_ref": "BOUNDARY.md#classification"}
        scope["subjects"][0]["commit"] = commit
        scope["probes"] = [dict(PROBE)]
        scope["challenge"] = dict(CHALLENGE)
        run = self.copy_fixture("toy-offer-run", self.tmp / "runs" / scope["run_id"])
        (run / "verifier" / "probes.py").write_text(PROBES_PY, encoding="utf-8")
        write_json(run / "SCOPE.json", scope)
        write_json(run / consent.FILE, {"events": []})
        state.new_state(run, NOW)
        lifecycle.pin(run)
        lifecycle.freeze(run, NOW, not_preregistered=True)
        runner.run(run, NOW)
        lifecycle.package(run, NOW)
        lifecycle.share(run, ORG, [], NOW)
        return run

    def test_report_publish_and_export(self):
        run = self.shared_run()
        report = (run / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("self-service over a pinned public boundary", report)
        self.assertIn("This run gives none", report)
        self.assertIn("`p1`", report)
        self.assertEqual(next_actions(run)["next_command"], "aacp run publish toy-offer")
        lifecycle.publish(run, NOW)
        self.assertEqual(state.load_state(run)["state"], "PUBLISHED")
        record = evidence_record(run)
        self.assertIn("Public boundary BOUNDARY.md", record["note"])
        self.assertIn("Runner probe p1 (BINDING_GAP): DEMONSTRATED", record["note"])
        self.assertIn("not consent and not endorsement", record["note"])

    def test_subject_maintainer_decline_allows_withhold(self):
        run = self.shared_run()
        with self.assertRaisesRegex(GateError, "withhold needs"):
            lifecycle.withhold(run, NOW)
        consent.add(run, "maintainer", "publication_declined", AGREE_REF, NOW)
        self.assertIn("withhold or answer", next_actions(run)["outstanding"][0]["action"])
        lifecycle.withhold(run, NOW)
        self.assertEqual(state.load_state(run)["state"], "WITHHELD")


if __name__ == "__main__":
    unittest.main()
