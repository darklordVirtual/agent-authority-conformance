import unittest

from conformance.lab import pins
from conformance.lab.errors import PinError
from tests.lab.helpers import LabTest, git


class PinsTest(LabTest):
    def setUp(self):
        super().setUp()
        self.repo, self.commit = self.remote_repo("subject", {
            "LICENSE": "Example licence\n", "src/a.py": "A = 1\n", "src/b.py": "B = 2\n", "other.txt": "x\n"})

    def scope(self, files):
        return {"subjects": [{"repo": self.repo, "commit": self.commit, "paths": ["src"], "files_sha256": files}]}

    def test_fetch_checks_out_exact_commit(self):
        # A later commit must not leak into a pinned fetch.
        (self.remotes / "subject" / "src" / "a.py").write_text("A = 99\n", encoding="utf-8")
        git("commit", "-qam", "later", cwd=self.remotes / "subject")
        clone = pins.fetch(self.repo, self.commit, self.tmp / "c")
        self.assertEqual((clone / "src" / "a.py").read_text(encoding="utf-8"), "A = 1\n")

    def test_unknown_commit_is_a_pin_error(self):
        with self.assertRaises(PinError):
            pins.fetch(self.repo, "f" * 40, self.tmp / "c")

    def test_materialize_exports_only_declared_paths_and_licence(self):
        clone = pins.fetch(self.repo, self.commit, self.tmp / "c")
        files = pins.hash_paths(clone, ["src"])
        self.assertEqual(sorted(files), ["src/a.py", "src/b.py"])
        trees, licenses = pins.materialize(self.scope(files), self.tmp / "work")
        self.assertTrue((trees[0] / "src" / "a.py").is_file())
        self.assertFalse((trees[0] / "other.txt").exists())
        self.assertEqual(licenses[0], "Example licence\n")

    def test_changed_byte_is_refused(self):
        clone = pins.fetch(self.repo, self.commit, self.tmp / "c")
        files = pins.hash_paths(clone, ["src"])
        files["src/a.py"] = "0" * 64
        with self.assertRaisesRegex(PinError, "src/a.py"):
            pins.materialize(self.scope(files), self.tmp / "work")

    def test_missing_file_is_refused(self):
        files = {"src/gone.py": "0" * 64}
        with self.assertRaisesRegex(PinError, "src/gone.py"):
            pins.materialize(self.scope(files), self.tmp / "work")

    def test_unpinned_extra_file_is_refused(self):
        clone = pins.fetch(self.repo, self.commit, self.tmp / "c")
        files = pins.hash_paths(clone, ["src"])
        del files["src/b.py"]
        with self.assertRaisesRegex(PinError, "unpinned"):
            pins.materialize(self.scope(files), self.tmp / "work")

    def test_missing_declared_path(self):
        clone = pins.fetch(self.repo, self.commit, self.tmp / "c")
        with self.assertRaisesRegex(PinError, "does not exist"):
            pins.hash_paths(clone, ["nope"])


if __name__ == "__main__":
    unittest.main()
