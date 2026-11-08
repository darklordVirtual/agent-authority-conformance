"""Release tooling: tag/version/changelog gates, notes, checksums and distribution checks.

Standard library only, so the CLI package job can run it without the dev dependencies.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
import zipfile

from scripts import release

VERSION = release.project_version()
TAG = f"v{VERSION}"


def fake_root(tmp: Path, version="1.2.0a3", changelog=None) -> Path:
    (tmp / "pyproject.toml").write_text(
        f'[project]\nname = "aacp-conformance"\nversion = "{version}"\n', encoding="utf-8")
    if changelog is None:
        changelog = f"# Changelog\n\n## {version} — alpha\n\n- First change.\n\n## 0.1 — draft\n\n- Old.\n"
    (tmp / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (tmp / "schema").mkdir()
    (tmp / "schema" / "one.schema.json").write_text('{"x": 1}\n', encoding="utf-8")
    return tmp


def build_fake_dist(root: Path, dist: Path, version: str, *, extra_wheel=None, schema_bytes=None,
                    entry="aacp = aacp.cli:main") -> None:
    dist.mkdir(parents=True, exist_ok=True)
    info = f"aacp_conformance-{version}.dist-info"
    members = {
        "aacp/__init__.py": b"",
        "aacp/cli.py": b"def main(): return 0\n",
        "conformance/lab/__init__.py": b"",
        "aacp/schemas/one.schema.json": schema_bytes or (root / "schema" / "one.schema.json").read_bytes(),
        f"{info}/METADATA": (f"Metadata-Version: 2.4\nName: aacp-conformance\nVersion: {version}\n"
                             "Requires-Python: >=3.12\n").encode(),
        f"{info}/entry_points.txt": f"[console_scripts]\n{entry}\n".encode(),
        f"{info}/licenses/LICENSE": b"Apache-2.0\n",
    }
    members.update(extra_wheel or {})
    with zipfile.ZipFile(dist / f"aacp_conformance-{version}-py3-none-any.whl", "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    prefix = f"aacp_conformance-{version}/"
    with tarfile.open(dist / f"aacp_conformance-{version}.tar.gz", "w:gz") as archive:
        for name, data in {"pyproject.toml": (root / "pyproject.toml").read_bytes(), "LICENSE": b"x",
                           "README.md": b"x", "PKG-INFO": b"x", "aacp/cli.py": b"x"}.items():
            entry_info = tarfile.TarInfo(prefix + name)
            entry_info.size = len(data)
            archive.addfile(entry_info, io.BytesIO(data))


class VersionTests(unittest.TestCase):
    def test_parse_tag_and_prerelease(self):
        self.assertEqual(release.parse_tag("v0.3.0a1"), "0.3.0a1")
        self.assertTrue(release.is_prerelease("0.3.0a1"))
        self.assertTrue(release.is_prerelease("1.0.0rc2"))
        self.assertTrue(release.is_prerelease("1.0.0.dev4"))
        self.assertFalse(release.is_prerelease("1.0.0"))
        self.assertFalse(release.is_prerelease("1.0"))

    def test_rejects_malformed_tags(self):
        for tag in ("0.3.0a1", "v0.3.0-alpha", "vlatest", "v1", "v0.3.0a1+local", "v0.3.0 a1"):
            with self.subTest(tag=tag), self.assertRaises(release.ReleaseError):
                release.parse_tag(tag)

    def test_titles(self):
        self.assertEqual(release.release_title("0.3.0a1"), "AACP v0.3.0a1 (alpha)")
        self.assertEqual(release.release_title("0.3.0rc1"), "AACP v0.3.0rc1 (release candidate)")
        self.assertEqual(release.release_title("1.0.0"), "AACP v1.0.0")

    def test_repository_version_is_releasable(self):
        # The changelog section is enforced at tag time, not on every development commit.
        meta = release.metadata(TAG, dry_run=True)
        self.assertEqual(meta["version"], VERSION)
        self.assertEqual(meta["wheel"], f"aacp_conformance-{VERSION}-py3-none-any.whl")


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_tag_must_match_pyproject(self):
        root = fake_root(self.tmp)
        with self.assertRaisesRegex(release.ReleaseError, "does not match"):
            release.metadata("v1.2.0a4", root)

    def test_changelog_section_required_unless_dry_run(self):
        root = fake_root(self.tmp, changelog="# Changelog\n\n## Unreleased\n\n- x\n")
        with self.assertRaisesRegex(release.ReleaseError, "no '## 1.2.0a3' section"):
            release.metadata("v1.2.0a3", root)
        self.assertEqual(release.metadata("v1.2.0a3", root, dry_run=True)["version"], "1.2.0a3")
        self.assertIn("Dry run", release.render_notes("v1.2.0a3", root, dry_run=True))
        with self.assertRaises(release.ReleaseError):
            release.render_notes("v1.2.0a3", root)

    def test_changelog_heading_must_match_exactly(self):
        root = fake_root(self.tmp, changelog="# Changelog\n\n## 1.2.0a30\n\n- wrong version\n")
        with self.assertRaises(release.ReleaseError):
            release.metadata("v1.2.0a3", root)

    def test_empty_changelog_section_rejected(self):
        root = fake_root(self.tmp, changelog="# Changelog\n\n## 1.2.0a3\n\n## 1.1\n\n- x\n")
        with self.assertRaisesRegex(release.ReleaseError, "empty"):
            release.metadata("v1.2.0a3", root)

    def test_notes_contain_only_this_version_and_verification(self):
        root = fake_root(self.tmp)
        notes = release.render_notes("v1.2.0a3", root)
        self.assertIn("- First change.", notes)
        self.assertNotIn("- Old.", notes)
        self.assertIn("gh attestation verify aacp_conformance-1.2.0a3-py3-none-any.whl", notes)
        self.assertIn("releases/download/v1.2.0a3/aacp_conformance-1.2.0a3-py3-none-any.whl", notes)
        self.assertIn("grants no certification", notes)
        self.assertTrue(notes.startswith("Pre-release"))

    def test_github_output_is_single_line(self):
        out = self.tmp / "out"
        release._write_github_output(str(out), {"prerelease": True, "version": "1.0"})
        self.assertEqual(out.read_text(encoding="utf-8"), "prerelease=true\nversion=1.0\n")
        with self.assertRaises(release.ReleaseError):
            release._write_github_output(str(out), {"bad": "a\nb"})


class ChecksumTests(unittest.TestCase):
    def setUp(self):
        self.dist = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dist)
        (self.dist / "b.whl").write_bytes(b"wheel")
        (self.dist / "a.tar.gz").write_bytes(b"sdist")

    def test_gnu_format_sorted_and_verifiable(self):
        path = release.write_checksums(self.dist)
        expected = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                           for name, data in (("a.tar.gz", b"sdist"), ("b.whl", b"wheel")))
        self.assertEqual(path.read_text(encoding="utf-8"), expected)
        self.assertEqual(release.verify_checksums(self.dist, expected_names=["a.tar.gz", "b.whl"])["verified"],
                         ["a.tar.gz", "b.whl"])

    def test_changed_byte_is_detected(self):
        release.write_checksums(self.dist)
        (self.dist / "b.whl").write_bytes(b"wheeL")
        with self.assertRaisesRegex(release.ReleaseError, "mismatch"):
            release.verify_checksums(self.dist)

    def test_missing_unexpected_and_malformed_entries(self):
        release.write_checksums(self.dist)
        with self.assertRaisesRegex(release.ReleaseError, "expected"):
            release.verify_checksums(self.dist, expected_names=["a.tar.gz", "b.whl", "c.cdx.json"])
        (self.dist / "a.tar.gz").unlink()
        with self.assertRaisesRegex(release.ReleaseError, "missing"):
            release.verify_checksums(self.dist)
        (self.dist / release.CHECKSUMS).write_text("deadbeef  ../escape\n", encoding="utf-8")
        with self.assertRaisesRegex(release.ReleaseError, "malformed"):
            release.verify_checksums(self.dist)


class DistributionTests(unittest.TestCase):
    version = "1.2.0a3"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "repo").mkdir()
        self.root = fake_root(self.tmp / "repo")
        self.dist = self.tmp / "dist"

    def check(self, **kwargs):
        return release.check_dist(self.dist, f"v{self.version}", self.root, **kwargs)

    def test_valid_distribution_and_reproducible_rebuild(self):
        build_fake_dist(self.root, self.dist, self.version)
        shutil.copytree(self.dist, self.tmp / "rebuild")
        self.assertTrue(self.check(rebuild=self.tmp / "rebuild")["reproducible"])

    def test_non_reproducible_wheel_rejected(self):
        build_fake_dist(self.root, self.dist, self.version)
        build_fake_dist(self.root, self.tmp / "rebuild", self.version, extra_wheel={"aacp/extra.py": b""})
        with self.assertRaisesRegex(release.ReleaseError, "not byte-reproducible"):
            self.check(rebuild=self.tmp / "rebuild")

    def test_unexpected_file_in_dist_rejected(self):
        build_fake_dist(self.root, self.dist, self.version)
        (self.dist / "stray.whl").write_bytes(b"")
        with self.assertRaisesRegex(release.ReleaseError, "exactly"):
            self.check()

    def test_lab_runs_never_ship(self):
        build_fake_dist(self.root, self.dist, self.version, extra_wheel={"runs/private/result.json": b"{}"})
        with self.assertRaisesRegex(release.ReleaseError, "forbidden"):
            self.check()

    def test_stale_schema_rejected(self):
        build_fake_dist(self.root, self.dist, self.version, schema_bytes=b'{"x": 2}\n')
        with self.assertRaisesRegex(release.ReleaseError, "differs"):
            self.check()

    def test_missing_console_script_rejected(self):
        build_fake_dist(self.root, self.dist, self.version, entry="aacp = elsewhere:main")
        with self.assertRaisesRegex(release.ReleaseError, "console script"):
            self.check()


if __name__ == "__main__":
    unittest.main()
