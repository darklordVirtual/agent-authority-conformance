"""The NTI witness example: RFC 8032 primitives, Merkle rules, and the full lab flow over a
synthetic package (bytes inputs, public boundary, challenge, probes, package, rerun, respond)."""

import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from conformance.lab import lifecycle, respond, runner, state
from conformance.lab.canonical import read_json
from conformance.lab.rerun import rerun
from tests.lab.helpers import NOW, LabTest
from tests.lab.nti_synthetic import NEW_SECRET, OLD_SECRET, build_repo, template_dir, verifier

SCHEMAS = Path(__file__).resolve().parents[2] / "schema" / "lab"

# RFC 8032 section 7.1, TEST 1, TEST 2 and TEST 3.
RFC8032 = [
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025", "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]
L = 2**252 + 27742317777372353535851937790883648493


class PrimitiveTest(unittest.TestCase):
    def setUp(self):
        self.v = verifier()

    def test_rfc8032_vectors_sign_and_verify(self):
        for secret, public, message, signature in RFC8032:
            with self.subTest(public=public[:8]):
                secret, public = bytes.fromhex(secret), bytes.fromhex(public)
                message, signature = bytes.fromhex(message), bytes.fromhex(signature)
                self.assertEqual(self.v.ed25519_public(secret), public)
                self.assertEqual(self.v.ed25519_sign(secret, message), signature)
                self.assertTrue(self.v.ed25519_verify(public, message, signature))
                self.assertFalse(self.v.ed25519_verify(public, message + b"x", signature))

    def test_malleated_s_is_rejected(self):
        _, public, message, signature = (bytes.fromhex(x) for x in RFC8032[1])
        s = int.from_bytes(signature[32:], "little") + L
        self.assertFalse(self.v.ed25519_verify(public, message, signature[:32] + s.to_bytes(32, "little")))

    def test_pem_round_trip_and_rejection(self):
        public = self.v.ed25519_public(NEW_SECRET)
        self.assertEqual(self.v.public_key_from_pem(self.v.pem_for(public)), public)
        self.assertIsNone(self.v.public_key_from_pem(b"-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n"))

    def test_documented_rule_equals_rfc6962_split(self):
        for n in range(1, 34):
            with self.subTest(n=n):
                leaves = self.v.probe_leaves(n)
                self.assertEqual(self.v.merkle_documented(leaves)[0], self.v.merkle_rfc6962(leaves))

    def test_duplicating_rule_collides_and_documented_rule_does_not(self):
        for n in (3, 5, 7, 9):
            leaves = self.v.probe_leaves(n)
            twin = leaves + [leaves[-1]]
            self.assertEqual(self.v.merkle_duplicating(leaves)[0], self.v.merkle_duplicating(twin)[0])
            self.assertNotEqual(self.v.merkle_documented(leaves)[0], self.v.merkle_documented(twin)[0])

    def test_rules_agree_on_powers_of_two(self):
        for n in (1, 2, 4, 8, 16):
            leaves = self.v.probe_leaves(n)
            self.assertEqual(self.v.merkle_documented(leaves)[0], self.v.merkle_duplicating(leaves)[0])


class NtiFlowTest(LabTest):
    def run_case(self, **variant):
        earlier, pinned = build_repo(self.remotes / "nti", **variant)
        run = lifecycle.init(self.tmp / "runs", "nti", None, NOW, template=template_dir(self, earlier, pinned))
        self.assertTrue((run / "verifier" / "nti_witness.py").is_file())  # copied from the run skeleton
        lifecycle.pin(run)
        lifecycle.freeze(run, NOW, not_preregistered=True)
        runner.run(run, NOW)
        return run

    def results(self, run):
        claims = {(r["claim"], r["input"]): r for r in read_json(run / "results" / "claims.json")["records"]}
        probes = {r["probe"]: r for r in read_json(run / "results" / "probes.json")["records"]}
        return claims, probes

    def test_full_flow_establishes_claims_and_demonstrates_probes(self):
        run = self.run_case()
        claims, probes = self.results(run)
        for claim in ("package_signature", "s6_seal"):
            for input_id in ("witness", "pages"):
                self.assertEqual(claims[(claim, input_id)]["result"], "ESTABLISHED", (claim, input_id))
        for claim in ("s4_digests", "s5_root", "manifest_hashes", "pages_mirror"):
            self.assertEqual(claims[(claim, "tree")]["result"], "ESTABLISHED", claim)
        for claim in ("suite_outcomes_evidenced", "key_anchor"):
            self.assertEqual(claims[(claim, "tree")]["result"], "NOT_ESTABLISHED")
            self.assertTrue(claims[(claim, "tree")]["unresolved_obligations"])
        self.assertTrue(all(p["observation"] == "DEMONSTRATED" for p in probes.values()),
                        {k: (p["observation"], p.get("verifier_error")) for k, p in probes.items()})
        self.assertFalse(probes["s5_documented_vs_implemented"]["affects_pinned_artifact"])
        self.assertFalse(probes["s5_leaf_count_binding"]["affects_pinned_artifact"])
        self.assertTrue(probes["s6_message_binding"]["affects_pinned_artifact"])
        self.assertEqual(probes["s5_documented_vs_implemented"]["witness"]["leaf_counts_where_roots_differ_1_to_8"],
                         [3, 5, 6, 7])
        v = verifier()
        rotation = probes["key_changed_between_revisions"]["witness"]
        self.assertEqual(rotation["pinned_key_raw_hex"], v.ed25519_public(NEW_SECRET).hex())
        self.assertEqual(rotation["earlier_key_raw_hex"], v.ed25519_public(OLD_SECRET).hex())
        schema = Draft202012Validator(json.loads((SCHEMAS / "probe-results.schema.json").read_text(encoding="utf-8")))
        schema.validate(read_json(run / "results" / "probes.json"))

    def test_package_rerun_and_respond(self):
        run = self.run_case()
        lifecycle.package(run, NOW)
        report = (run / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("pinned public boundary", report)
        self.assertIn("## Challenge", report)
        self.assertIn("## Probes (runner findings, not claim results)", report)
        outcome, details = rerun(run)
        self.assertEqual(outcome, "REPRODUCED", details)
        path = respond.write(run, drafted_by="agent:test", ai_assisted=True)
        # Resolved on both sides: on macOS a temporary directory is reached
        # through /var, a symlink to /private/var.
        self.assertEqual(path.resolve(), (run / respond.DEFAULT_OUT).resolve())
        text = path.read_text(encoding="utf-8")
        root = read_json(run / "results" / "probes.json")["records"][2]["witness"]["s5_root_after_relabel"]
        self.assertIn(root, text)
        self.assertIn("This response gives none", text)
        holding = text.index("#### Holding for the pinned bytes as published")
        constructed = text.index("#### Shown only on constructed inputs")
        self.assertLess(holding, constructed)
        self.assertGreater(text.index("`s5_leaf_count_binding`"), constructed)
        self.assertLess(text.index("`s6_message_binding`"), constructed)
        self.assertIn("Drafted by agent:test; AI-assisted: yes", text)
        self.assertIn(state.load_state(run)["plan_sha256"], text)
        for key in ("score", "overall", "aggregate", "total", "grade"):
            self.assertNotIn(f'"{key}"', text)  # no aggregate field in any rendered record
        self.assertEqual(rerun(run)[0], "REPRODUCED")  # the draft lives outside the manifest

    def test_respond_never_overwrites_run_records(self):
        from conformance.lab.errors import GateError
        run = self.run_case()
        lifecycle.package(run, NOW)
        scope_bytes = (run / "SCOPE.json").read_bytes()
        for target in (run / "SCOPE.json", run / "results" / "claims.json", run / "MANIFEST.json",
                       run / "notes.md", run):
            with self.subTest(target=target.name), self.assertRaisesRegex(GateError, "run directory|not a file"):
                respond.write(run, out=target)
        link = self.tmp / "innocent.md"
        link.symlink_to(run / "SCOPE.json")
        with self.assertRaisesRegex(GateError, "run directory"):
            respond.write(run, out=link)
        self.assertEqual((run / "SCOPE.json").read_bytes(), scope_bytes)
        respond.write(run)
        with self.assertRaisesRegex(GateError, "--force"):
            respond.write(run)
        respond.write(run, force=True)
        outside = respond.write(run, out=self.tmp / "reply.md")
        self.assertTrue(outside.is_file())
        self.assertEqual(rerun(run)[0], "REPRODUCED")

    def test_changed_byte_contradicts_signature(self):
        run = self.run_case(tamper=True)
        claims, _ = self.results(run)
        self.assertEqual(claims[("package_signature", "witness")]["result"], "CONTRADICTED")
        self.assertEqual(claims[("s6_seal", "witness")]["result"], "ESTABLISHED")  # the seal does not cover it

    def test_missing_signature_is_a_non_verdict(self):
        run = self.run_case(missing_signature=True)
        claims, probes = self.results(run)
        record = claims[("package_signature", "witness")]
        self.assertEqual((record["execution"], record["result"]), ("INVALID_INPUT", None))
        self.assertEqual(claims[("pages_mirror", "tree")]["result"], "CONTRADICTED")
        self.assertEqual(probes["package_signature_framing"]["execution"], "INVALID_INPUT")

    def test_terminology_probe_discriminates_a_recorded_change(self):
        _, probes = self.results(self.run_case())
        w = probes["s4_s5_s6_meaning_changed"]["witness"]
        self.assertEqual(w["earlier_status_in_results"], {"S4": "NOT_RUN", "S5": "NOT_RUN", "S6": "NOT_RUN"})
        self.assertTrue(w["pinned_meaning"]["S5"].startswith("S5 evidence root: Merkle root"))
        self.assertNotIn("source", probes["s4_s5_s6_meaning_changed"]["message"].split("terminology only")[0].lower())

    def test_terminology_probe_is_quiet_when_the_change_is_recorded(self):
        _, probes = self.results(self.run_case(records_change=True))
        self.assertEqual(probes["s4_s5_s6_meaning_changed"]["observation"], "NOT_DEMONSTRATED")

    def test_respond_refuses_before_run_and_after_edit(self):
        earlier, pinned = build_repo(self.remotes / "nti")
        run = lifecycle.init(self.tmp / "runs", "nti", None, NOW, template=template_dir(self, earlier, pinned))
        from conformance.lab.errors import GateError, PackageError
        with self.assertRaisesRegex(GateError, "measured run"):
            respond.render(run)
        lifecycle.pin(run)
        lifecycle.freeze(run, NOW, not_preregistered=True)
        runner.run(run, NOW)
        path = run / "results" / "claims.json"
        path.write_text(path.read_text(encoding="utf-8").replace("ESTABLISHED", "CONTRADICTED", 1), encoding="utf-8")
        with self.assertRaisesRegex(PackageError, "results/"):
            respond.render(run)
        with self.assertRaisesRegex(GateError, "agent:<id>"):
            respond.write(run, drafted_by="robot")

    def test_digests_are_the_pinned_bytes(self):
        run = self.run_case()
        scope = read_json(run / "SCOPE.json")
        pinned = scope["subjects"][0]["files_sha256"]
        record = next(r for r in read_json(run / "results" / "claims.json")["records"] if r["input"] == "witness")
        bundle = {k.removeprefix("conformance/witness/"): v for k, v in pinned.items()
                  if k.startswith("conformance/witness/")}
        from conformance.lab.canonical import sha256_json
        self.assertEqual(record["evidence"], [f"sha256:{sha256_json(bundle)}"])
        self.assertEqual(hashlib.sha256((self.remotes / "nti" / "conformance/witness/README.md").read_bytes()).hexdigest(),
                         scope["public_boundary"]["sha256"])


if __name__ == "__main__":
    unittest.main()
