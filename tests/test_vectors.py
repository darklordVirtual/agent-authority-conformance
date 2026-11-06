"""The frozen reference vectors: their bytes, their sources, and the runner's judgement."""

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from conformance import vectors as V
from conformance.lab.canonical import FORBIDDEN_KEYS, find_forbidden_keys

ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = ROOT / "vectors" / V.SUITE
BUILD = ROOT / "scripts" / "build_reference_vectors.py"
EXAMPLE = ROOT / "templates" / "vector-impl" / "stdlib_impl.py"
#: The frozen suite is pinned by the digest of its manifest, which pins every file.
MANIFEST_SHA256 = "23434533345cee99d7be63dcf02f6a93c3dd7d3f33e18a9b3673471cb322a7d4"


def _build_module():
    spec = importlib.util.spec_from_file_location("build_reference_vectors", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _quiet(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fn(*args)
    return code, out.getvalue(), err.getvalue()


class FrozenBytes(unittest.TestCase):
    def test_the_manifest_is_the_pinned_one(self):
        data = (SUITE_DIR / "MANIFEST.json").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), MANIFEST_SHA256,
                         "v1 is frozen: a changed vector needs a new suite version")

    def test_every_digest_matches(self):
        self.assertEqual(V.verify_suite(SUITE_DIR), [])

    def test_the_suite_reproduces_from_its_sources(self):
        code, out, err = _quiet(_build_module().main, ["--check"])
        self.assertEqual(code, 0, err)

    def test_a_changed_byte_is_found_and_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / V.SUITE
            shutil.copytree(SUITE_DIR, copy)
            path = copy / "lab.canonical_json.json"
            data = bytearray(path.read_bytes())
            data[data.index(b"h\xc3\xa9llo")] = ord("H")
            path.write_bytes(bytes(data))
            problems = V.verify_suite(copy)
        self.assertTrue(any(p.startswith("lab.canonical_json.json: sha256") for p in problems),
                        problems)

    def test_a_missing_or_unlisted_file_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / V.SUITE
            shutil.copytree(SUITE_DIR, copy)
            (copy / "lab.read_json.json").unlink()
            (copy / "extra.json").write_text("{}", encoding="utf-8")
            problems = V.verify_suite(copy)
        self.assertIn("lab.read_json.json: listed in MANIFEST.json, absent", problems)
        self.assertIn("extra.json: present but not listed", problems)

    def test_a_rewritten_manifest_is_caught_by_sha256sums(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / V.SUITE
            shutil.copytree(SUITE_DIR, copy)
            manifest = json.loads((copy / "MANIFEST.json").read_text(encoding="utf-8"))
            manifest["status"] = "draft"
            (copy / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            problems = V.verify_suite(copy)
        self.assertIn("MANIFEST.json: its digest in SHA256SUMS does not match", problems)

    def test_write_refuses_to_replace_a_frozen_suite(self):
        code, out, err = _quiet(_build_module().main, ["--write"])
        self.assertEqual(code, 1)
        self.assertIn("never rewritten", err)


class Sources(unittest.TestCase):
    def test_the_build_never_imports_the_rules_it_checks(self):
        tree = ast.parse(BUILD.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertFalse({m for m in imported if m.startswith("conformance")}, imported)

    def test_every_vector_names_where_its_answer_comes_from(self):
        allowed = ("fixture:", "producer:", "specification:")
        for doc in V.load_operations(SUITE_DIR):
            for v in doc["vectors"]:
                with self.subTest(vector=v["id"]):
                    self.assertTrue(v["expected_source"].startswith(allowed), v["expected_source"])
                    path = v["expected_source"].split(":", 1)[1].split(" ")[0]
                    self.assertTrue((ROOT / path).exists(), path)

    def test_the_e_rule_vectors_are_the_fixtures_verbatim(self):
        [doc] = [d for d in V.load_operations(SUITE_DIR) if d["operation"] == "e_rule.evaluate"]
        fixtures = sorted((ROOT / "tests" / "fixtures").glob("*.json"))
        self.assertEqual(len(doc["vectors"]), len(fixtures))
        for v, path in zip(doc["vectors"], fixtures):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((v["input"], v["expected"]["result"]),
                             (fixture["input"], fixture["expected"]))

    def test_the_suite_itself_holds_no_aggregate_key(self):
        for path in SUITE_DIR.glob("*.json"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            stripped = doc if path.name == "MANIFEST.json" else {
                k: v for k, v in doc.items() if k != "vectors"}
            self.assertEqual(find_forbidden_keys(stripped), [], path.name)


class Judgement(unittest.TestCase):
    def setUp(self):
        self.ops = V.load_operations(SUITE_DIR)
        self.reference = V._reference()

    def _report(self, respond):
        return V.report(self.ops, respond, None)

    def test_the_reference_agrees_with_every_vector(self):
        rep = self._report(lambda r: V.answer(r, self.reference))
        for op in rep["operations"]:
            self.assertEqual(op["by_outcome"][V.AGREES], [v["id"] for v in op["vectors"]],
                             op["operation"])

    def test_a_wrong_answer_is_a_disagreement_and_fails_the_run(self):
        def wrong(request):
            out = V.answer(request, self.reference)
            if request["vector_id"] == "e-bounded-pass":
                out = json.loads(json.dumps(out).replace('"PASS"', '"FAIL"'))
            return out
        rep = self._report(wrong)
        [e] = [op for op in rep["operations"] if op["operation"] == "e_rule.evaluate"]
        self.assertEqual(e["by_outcome"][V.DISAGREES], ["e-bounded-pass"])
        self.assertTrue(V._failed(rep))

    def test_true_is_not_one_and_one_point_oh_is_not_one(self):
        self.assertFalse(V._same({"result": True}, {"result": 1}, None))
        self.assertFalse(V._same({"result": {"n": 1.0}}, {"result": {"n": 1}}, None))
        self.assertFalse(V._same({"result": 1}, {"result": 1, "extra": 0}, None))
        self.assertFalse(V._same({"error": "X"}, {"result": None}, None))

    def test_compare_limits_the_keys_judged(self):
        expected = {"result": {"result": "INVALID_INPUT", "unmet_obligation": None,
                               "reason": "x"}}
        self.assertTrue(V._same(expected, {"result": {"result": "INVALID_INPUT",
                                                      "unmet_obligation": None,
                                                      "reason": "other wording"}},
                                ["result", "unmet_obligation"]))
        self.assertFalse(V._same(expected, {"result": {"result": "INVALID_INPUT"}},
                                 ["result", "unmet_obligation"]))

    def test_an_unsupported_operation_is_not_implemented_not_a_failure(self):
        rep = self._report(lambda r: {"error": "UNSUPPORTED_OPERATION"})
        self.assertFalse(V._failed(rep))
        for op in rep["operations"]:
            self.assertEqual(op["by_outcome"][V.AGREES], [])

    def test_the_report_holds_no_aggregate_key(self):
        rep = self._report(lambda r: V.answer(r, self.reference))
        self.assertEqual(find_forbidden_keys(rep), [])
        self.assertTrue(FORBIDDEN_KEYS)


class Subprocess(unittest.TestCase):
    def _run(self, script, timeout=20.0):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "impl.py"
            path.write_text(script, encoding="utf-8")
            respond = V._subprocess_responder([sys.executable, str(path)], timeout)
            request = {"operation": "lab.read_json", "vector_id": "x", "input": {"text": "{}"}}
            try:
                return respond(request)
            except V._ImplementationFailed as exc:
                return f"FAILED: {exc}"

    def test_a_crash_is_an_error_with_its_exit_status(self):
        self.assertTrue(self._run("import sys; sys.exit(3)").startswith("FAILED: exit status 3"))

    def test_two_lines_are_an_error(self):
        self.assertIn("expected one JSON line, got 2",
                      self._run('print("{}"); print("{}")'))

    def test_a_line_separator_inside_json_is_one_line(self):
        # The child writes the UTF-8 bytes of U+2028 inside a JSON string.
        script = ("import sys; sys.stdin.read(); "
                  "sys.stdout.buffer.write(b'{\"result\": \"a\\xe2\\x80\\xa8b\"}\\n')")
        self.assertEqual(self._run(script), {"result": "a" + chr(0x2028) + "b"})

    def test_text_that_is_not_json_is_an_error(self):
        self.assertIn("not JSON", self._run('print("hello")'))

    def test_a_hang_is_an_error_after_the_timeout(self):
        self.assertIn("no answer within", self._run("import time; time.sleep(5)", timeout=0.5))

    def test_the_cli_exits_non_zero_on_a_wrong_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "liar.py"
            path.write_text('import json,sys; json.load(sys.stdin); '
                            'print(json.dumps({"result": []}))', encoding="utf-8")
            code, out, err = _quiet(V.main, ["run", "--operations", "lab.forbidden_keys",
                                             "--impl", f"{sys.executable} {path}"])
        self.assertEqual(code, 1)
        self.assertIn("DISAGREES agg-top-level-score", out)

    def test_the_stdlib_example_agrees_where_it_implements(self):
        code, out, err = _quiet(V.main, ["run", "--impl", f"{sys.executable} {EXAMPLE}"])
        self.assertEqual(code, 0, out + err)
        self.assertIn("oe08.observation_vantage: agrees 15", out)
        self.assertIn("e_rule.evaluate: not implemented 21", out)


if __name__ == "__main__":
    unittest.main()
