"""A synthetic NTI-style witness package for tests, signed with test keys.

Two commits in one local repository: an earlier revision (old key, external attribution)
and the pinned revision (new key, the README rule text, a generator and verifier whose
odd-node lines are present as text only). Nothing here is the producer's bytes.
"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

from conformance.lab.canonical import read_json, write_json
from tests.lab.helpers import commit_files, make_repo

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "templates" / "runs" / "nti-witness"
REPO = "https://example.invalid/nti"
OLD_SECRET = bytes(range(32))
NEW_SECRET = bytes(range(32, 64))


def verifier():
    spec = importlib.util.spec_from_file_location("nti_witness_under_test", EXAMPLE / "verifier" / "nti_witness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dumps(obj):
    return (json.dumps(obj, indent=2) + "\n").encode("utf-8")


FIXTURE = _dumps({
    "classification": "SYNTHETIC - test fixture, not production evidence",
    "artifacts": [{"name": "request.json", "content_utf8": "{\"scope\":\"read\"}"},
                  {"name": "policy.txt", "content_utf8": "allow if scope is read"},
                  {"name": "audit_note.txt", "content_utf8": "synthetic audit entry"}]})

README = (b"# Witness\n\n| Seal | Field | Construction |\n| :--- | :--- | :--- |\n"
          b"| **S4** file integrity | `S4_file_integrity` | SHA-256 of each artifact. |\n"
          b"| **S5** evidence root | `S5_evidence_root` | Merkle root. Odd nodes are promoted unchanged. |\n"
          b"| **S6** seal | `S6_hmac_seal` | Ed25519 signature over the S5 root. |\n\n"
          b"The field is called `S6_hmac_seal` to match the witness\nspecification, but it is a signature.\n\n"
          b"This is a native implementation. It shares no code with any external conformance kit. The\n"
          b"generator is in the repository.\n")
GENERATOR = (b"def _merkle_root(level):\n    for i in range(0, len(level), 2):\n"
             b"            right = level[i + 1] if i + 1 < len(level) else level[i]\n")
VERIFY = (b"#!/usr/bin/env bash\nwhile len(lv) > 1:\n"
          b"    lv = [hashlib.sha256(N + lv[i] + (lv[i+1] if i+1 < len(lv) else lv[i])).digest()\n")
SIGN = b"#!/usr/bin/env bash\ncat \"$HERE/RESULTS.json\" \"$HERE/MANIFEST.json\" > \"$HERE/.to_sign.bin\"\n"
CORE_TESTS = b"#[test]\nfn core() {}\n"


def _package(v, secret, readme, extra_results=None, manifest_entries=()):
    raw = FIXTURE
    s4 = [{"name": "evidence_package.json", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}]
    for a in json.loads(raw)["artifacts"]:
        data = a["content_utf8"].encode()
        s4.append({"name": a["name"], "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    root, levels = v.merkle_documented([bytes.fromhex(e["sha256"]) for e in s4])
    results = {"overall_status": "PASSED",
               "suites": [{"id": "rust", "status": "PASSED", "total_passed": 3, "total_failed": 0}],
               "S4_file_integrity": s4,
               "S5_evidence_root": {"merkle_root_sha256": root.hex(), "leaf_count": len(s4),
                                    "levels": [[h.hex() for h in lv] for lv in levels]},
               "S6_hmac_seal": {"scheme": "Ed25519", "signed_over": "S5_evidence_root.merkle_root_sha256",
                                "seal_hex": v.ed25519_sign(secret, root).hex()},
               "seal_scope": {"evidence_file": "conformance/witness_generator/sample_evidence.json",
                              "classification": "SYNTHETIC - test fixture, not production evidence"}}
    results.update(extra_results or {})
    manifest = {"nti_test_scripts": [dict(e) for e in manifest_entries], "witness_generator": [
        {"path": "conformance/witness_generator/generate_seals.py", "sha256": hashlib.sha256(GENERATOR).hexdigest()},
        {"path": "conformance/witness_generator/sample_evidence.json", "sha256": hashlib.sha256(raw).hexdigest()}]}
    r, m = _dumps(results), _dumps(manifest)
    return {"RESULTS.json": r, "MANIFEST.json": m, "SIGNATURE.sig": v.ed25519_sign(secret, r + m),
            "PUBLIC_KEY.pem": v.pem_for(v.ed25519_public(secret)), "README.md": readme}


def build_repo(root, tamper=False, missing_signature=False, records_change=False):
    """Create the repository; return (earlier commit, pinned commit)."""
    v = verifier()
    old = _package(v, OLD_SECRET, b"# Witness\n\nS4, S5 and S6 are ASL invariants and were not run.\n",
                   extra_results={"external": [{"id": "S4", "status": "NOT_RUN"}, {"id": "S5", "status": "NOT_RUN"},
                                               {"id": "S6", "status": "NOT_RUN"}]})
    history = {f"conformance/witness/{k}": d for k, d in old.items()}
    history["conformance/witness/vendor/S4_S5_S6_RECORD.json"] = _dumps({"invariants": {
        "S4": "Thresholds are quiet on ordinary traffic, but the tripwire still fires.",
        "S5": "Every kill path still fires the complete cascade.",
        "S6": "Not defined in the public conformance kit revision."}})
    earlier = make_repo(root, history)
    core = [{"path": "ube-foundation/tests/core_tests.rs", "sha256": hashlib.sha256(CORE_TESTS).hexdigest()}]
    new = _package(v, NEW_SECRET, README, manifest_entries=core)
    if tamper:
        new["RESULTS.json"] = new["RESULTS.json"].replace(b"PASSED", b"PASSEd", 1)
    files = {f"conformance/witness/{k}": d for k, d in new.items()}
    files.update({f"docs/witness/{k}": d for k, d in new.items()})
    if records_change:
        files["conformance/witness/CHANGES.md"] = b"S4/S5/S6 previously named ASL invariants; they now name the seals.\n"
    remove = ["conformance/witness/vendor/S4_S5_S6_RECORD.json"]
    if missing_signature:
        del files["conformance/witness/SIGNATURE.sig"]
        remove.append("conformance/witness/SIGNATURE.sig")  # the earlier commit had one
    files.update({"conformance/witness/verify.sh": VERIFY, "conformance/witness/sign.sh": SIGN,
                  "conformance/witness_generator/generate_seals.py": GENERATOR,
                  "conformance/witness_generator/sample_evidence.json": FIXTURE,
                  "ube-foundation/tests/core_tests.rs": CORE_TESTS})
    pinned = commit_files(root, files, remove=remove)
    return earlier, pinned


def scope_for(earlier, pinned):
    """The committed example scope, pointed at the synthetic repository."""
    scope = copy.deepcopy(read_json(EXAMPLE / "SCOPE.json"))
    for subject, commit in zip(scope["subjects"], (pinned, earlier)):
        subject["repo"], subject["commit"] = REPO, commit
    scope["subjects"][0]["paths"] = ["conformance/witness", "conformance/witness_generator", "docs/witness",
                                     "ube-foundation/tests"]
    scope["public_boundary"].update(repo=REPO, commit=pinned, sha256=hashlib.sha256(README).hexdigest())
    scope["subjects"][1]["paths"] = ["conformance/witness"]
    for probe in scope["probes"]:
        probe["source_locators"] = [dict(loc, lines="1", path=loc["path"].replace(
            "vendor/S4_S5_S6_PROVENANCE.md", "vendor/S4_S5_S6_RECORD.json")) for loc in probe.get("source_locators", [])]
    return scope


def template_dir(test, earlier, pinned):
    """A run skeleton (SCOPE.json and verifier/) that init --template copies."""
    import shutil
    base = test.tmp / "template"
    shutil.copytree(EXAMPLE / "verifier", base / "verifier", ignore=shutil.ignore_patterns("__pycache__"))
    write_json(base / "SCOPE.json", scope_for(earlier, pinned))
    return base / "SCOPE.json"
