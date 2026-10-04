import tempfile
import unittest
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from conformance.adapter import (
    AdapterError, canonical_json, resolve, sha256_bytes, validate_manifest, write_run_package,
)

class AdapterTests(unittest.TestCase):
    def manifest(self, content=b"evidence\n"):
        return {
            "schema_version":"federation-adapter-v1",
            "subject":{"repository":"example/project","revision":"a"*40},
            "adapter":{"id":"example-v1","revision":"b"*40},
            "artifacts":[{"id":"e1","path":"evidence.txt","sha256":sha256_bytes(content),"source_class":"test_fixture","required":True}],
            "claims":[{
                "claim_id":"c1",
                "native_claim":{"producer":"example/project","claim_id":"native-c1","result_vocabulary":["ESTABLISHED","CONTRADICTED","NOT_ESTABLISHED"]},
                "aac_mapping":{"property":"C","relationship":"partial","rationale":"Fixture resolution alone does not establish exact-call integrity."},
                "procedure":"example-v1","artifacts":["e1"],
                "claim_ceiling":"Only the pinned fixture bytes were resolved."
            }],
            "explicit_non_claims":["production enforcement"],
            "review":{
                "mode":"PUBLIC_AFTER_REVIEW",
                "producer_review":"REQUIRED",
                "review_window_days":7,
                "unresolved_disagreement":"PUBLISH_WITH_DISAGREEMENT"
            }
        }

    def test_resolved_is_not_a_property_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"evidence\n")
            out=resolve(self.manifest(),d)
            self.assertEqual(out["adapter_status"],"RESOLVED")
            self.assertEqual(out["claims"][0]["evidence_resolution"],"RESOLVED")
            self.assertIsNone(out["claims"][0]["property_verdict"])
            self.assertFalse(out["publication_authorized"])
            self.assertEqual(out["review_state"],"PENDING_REVIEW_WINDOW")

    def test_public_immediate_is_explicit_not_inferred(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"evidence\n")
            m=self.manifest(); m["review"]["mode"]="PUBLIC_IMMEDIATE"; m["review"]["review_window_days"]=None
            out=resolve(m,d)
            self.assertTrue(out["publication_authorized"])
            self.assertEqual(out["review_state"],"PUBLICATION_ALLOWED")

    def test_legacy_review_is_private(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"evidence\n")
            m=self.manifest(); m["review"]={"maintainer_review_required":True}
            out=resolve(m,d)
            self.assertFalse(out["publication_authorized"])
            self.assertEqual(out["review_state"],"DRAFT_PRIVATE_REVIEW")

    def test_hash_mismatch_is_invalid_input_not_fail(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"changed")
            out=resolve(self.manifest(),d)
            self.assertEqual(out["adapter_status"],"INVALID_INPUT")
            self.assertEqual(out["evidence"][0]["resolution"],"HASH_MISMATCH")
            self.assertIsNone(out["claims"][0]["property_verdict"])

    def test_missing_is_invalid_input_not_fail(self):
        with tempfile.TemporaryDirectory() as d:
            out=resolve(self.manifest(),d)
            self.assertEqual(out["evidence"][0]["resolution"],"MISSING")
            self.assertIsNone(out["claims"][0]["property_verdict"])

    def test_deterministic_output(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"evidence.txt").write_bytes(b"evidence\n")
            self.assertEqual(resolve(self.manifest(),d),resolve(self.manifest(),d))

    def test_cli_reports_resolution_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "adapter.json"
            manifest.write_text(json.dumps(self.manifest()), encoding="utf-8")
            output = root / "bundle.json"
            command = [sys.executable, "-m", "scripts.run_federation_adapter",
                       "--manifest", str(manifest), "--subject-root", directory,
                       "--out", str(output)]
            for content, expected_code in [(None, 1), (b"changed", 1), (b"evidence\n", 0)]:
                with self.subTest(content=content):
                    if content is not None:
                        (root / "evidence.txt").write_bytes(content)
                    result = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected_code, result.stderr)
                    bundle = json.loads(output.read_text(encoding="utf-8"))
                    self.assertIsNone(bundle["claims"][0]["property_verdict"])
                    self.assertEqual(bundle["adapter_status"],
                                     "RESOLVED" if expected_code == 0 else "INVALID_INPUT")

    def test_rejects_relative_traversal(self):
        m=self.manifest(); m["artifacts"][0]["path"]="../secret"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_cli_run_checks_subject_pin_and_withholds_review_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subject = root / "subject"
            subject.mkdir()
            subprocess.run(["git", "init", "-q", str(subject)], check=True, capture_output=True)
            (subject / "evidence.txt").write_bytes(b"evidence\n")
            subprocess.run(["git", "-C", str(subject), "add", "evidence.txt"], check=True)
            subprocess.run(["git", "-C", str(subject), "-c", "user.name=Test",
                            "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
            revision = subprocess.run(["git", "-C", str(subject), "rev-parse", "HEAD"],
                                      check=True, capture_output=True, text=True).stdout.strip()
            manifest = self.manifest()
            manifest["subject"]["revision"] = revision
            manifest_path = root / "adapter.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            output = root / "run"
            summary = root / "summary.md"
            command = [sys.executable, "-m", "scripts.run_federation_adapter",
                       "--manifest", str(manifest_path), "--subject-root", str(subject),
                       "--record-dir", str(output), "--runner", "test-operator",
                       "--fixture-author", "test-author", "--summary", str(summary)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads((output / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(record["environment"]["subject_checkout_revision"], revision)
            self.assertEqual(record["environment"]["input_manifest_raw_sha256"],
                             sha256_bytes(manifest_path.read_bytes()))
            self.assertIn("withheld", summary.read_text())
            self.assertNotIn("| Artifact", summary.read_text())
            manifest["subject"]["revision"] = "a"*40
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            command[command.index(str(output))] = str(root / "wrong-pin")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checkout HEAD differs", result.stderr)
            self.assertFalse((root / "wrong-pin").exists())

    def test_run_package_has_verifiable_digests_and_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.manifest()
            bundle = resolve(manifest, directory)
            output = Path(directory) / "run"

            def write_package(path, runner="operator"):
                return write_run_package(
                    manifest, bundle, path, revision="c"*40, runner=runner,
                    fixture_author="fixture-author", classification="AUTHOR_RUN",
                    command="python -m scripts.run_federation_adapter",
                    environment={"python": "3.12"},
                )

            record = write_package(output)
            self.assertEqual(record["pins"]["adapter_revision"], "c"*40)
            self.assertEqual(record["output_sha256"], sha256_bytes((output / "bundle.json").read_bytes()))
            for line in (output / "SHA256SUMS").read_text().splitlines():
                digest, name = line.split("  ")
                self.assertEqual(digest, sha256_bytes((output / name).read_bytes()))
            identity = record.pop("run_id")
            self.assertEqual(identity, "resolution-sha256:" + sha256_bytes(canonical_json(record)))
            repeated = write_package(Path(directory) / "repeat")
            self.assertEqual(identity, repeated["run_id"])
            changed = write_package(Path(directory) / "changed", runner="another-operator")
            self.assertNotEqual(identity, changed["run_id"])
            with self.assertRaises(FileExistsError):
                write_package(output)

    def test_resolution_run_cannot_claim_independent_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.manifest()
            with self.assertRaises(AdapterError):
                write_run_package(manifest, resolve(manifest, directory), Path(directory) / "run",
                                  revision="c"*40, runner="operator", fixture_author="author",
                                  classification="INDEPENDENT_IMPLEMENTATION", command="resolve",
                                  environment={})

    def test_summary_publication_gate_and_public_invalid_input(self):
        from scripts.run_federation_adapter import ROOT, main

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mode, dirty, content in [
                ("PUBLIC_IMMEDIATE", False, b"evidence\n"),
                ("PUBLIC_IMMEDIATE", False, b"changed"),
                ("PUBLIC_IMMEDIATE", True, b"evidence\n"),
                ("PRIVATE_UNTIL_APPROVED", False, b"evidence\n"),
                ("PUBLIC_BY_MUTUAL_CONSENT", False, b"evidence\n"),
                ("PUBLIC_AFTER_REVIEW", False, b"evidence\n"),
            ]:
                with self.subTest(mode=mode, dirty=dirty, content=content):
                    manifest = self.manifest()
                    manifest["review"]["mode"] = mode
                    (root / "evidence.txt").write_bytes(content)
                    manifest_path = root / "adapter.json"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    output = root / f"run-{mode}-{dirty}-{content.hex()}"
                    summary = root / "summary.md"
                    arguments = ["resolver", "--manifest", str(manifest_path),
                                 "--subject-root", directory, "--record-dir", str(output),
                                 "--runner", "test-operator", "--fixture-author", "test-author",
                                 "--summary", str(summary)]

                    def git_fact(checkout, *arguments):
                        if arguments[0] == "status":
                            return " M conformance/adapter.py" if dirty else ""
                        return "c"*40 if checkout == ROOT else "a"*40

                    with patch.object(sys, "argv", arguments), patch(
                        "scripts.run_federation_adapter.git_output", side_effect=git_fact
                    ):
                        self.assertEqual(main(), 0 if content == b"evidence\n" else 1)
                    text = summary.read_text(encoding="utf-8")
                    public = mode == "PUBLIC_IMMEDIATE" and not dirty
                    self.assertEqual("| Artifact ID" in text, public)
                    self.assertEqual("withheld" in text, not public)
                    self.assertIn("SHA256SUMS SHA-256", text)
                    if public and content == b"changed":
                        self.assertIn("INVALID_INPUT", text)
                        self.assertIn("HASH_MISMATCH", text)

    def test_rejects_absolute_artifact_path(self):
        m=self.manifest(); m["artifacts"][0]["path"]="/tmp/evidence"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_duplicate_artifact_ids(self):
        m=self.manifest(); m["artifacts"].append(dict(m["artifacts"][0]))
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_unpinned_adapter_revision(self):
        m=self.manifest(); m["adapter"]["revision"]="main"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_short_revision(self):
        m=self.manifest(); m["subject"]["revision"]="main"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_verdict_in_adapter_claim(self):
        m=self.manifest(); m["claims"][0]["status"]="PASS"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_unknown_artifact_reference(self):
        m=self.manifest(); m["claims"][0]["artifacts"]=["missing"]
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_rejects_unknown_mapping_relationship(self):
        m=self.manifest(); m["claims"][0]["aac_mapping"]["relationship"]="equivalent"
        with self.assertRaises(AdapterError): validate_manifest(m)

    def test_public_after_review_requires_window(self):
        m=self.manifest(); m["review"]["review_window_days"]=None
        with self.assertRaises(AdapterError): validate_manifest(m)

if __name__=="__main__":
    unittest.main()
