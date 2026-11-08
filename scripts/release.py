"""Release helpers for GitHub Release distribution. Standard library only.

Every subcommand is read-only with respect to tracked files and fails closed:
a mismatch between the tag, the package version, the changelog or the built
distributions stops the release before anything is published.

    python scripts/release.py metadata --tag v0.3.0a1 [--dry-run] [--github-output FILE]
    python scripts/release.py notes --tag v0.3.0a1 [--dry-run] --out NOTES.md
    python scripts/release.py check-dist --dist dist --tag v0.3.0a1 [--rebuild-dist DIR]
    python scripts/release.py checksums --dist dist [--out dist/SHA256SUMS.txt]
    python scripts/release.py verify-checksums --dist dist [--tag v0.3.0a1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
import tomllib
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "aacp-conformance"
DIST_STEM = "aacp_conformance"
REPOSITORY = "darklordVirtual/agent-authority-conformance"
CHECKSUMS = "SHA256SUMS.txt"
# PEP 440 public version, restricted to the forms this project uses.
VERSION_RE = re.compile(r"^(?P<release>\d+(?:\.\d+){1,2})(?P<pre>(?:a|b|rc)\d+)?(?P<dev>\.dev\d+)?$")
# Paths that must never ship in an installable artifact (see .gitignore: runs hold unreleased results).
FORBIDDEN_PARTS = ("runs/", ".github/", ".git/", "__pycache__/", ".venv/")


class ReleaseError(RuntimeError):
    pass


def project_version(root: Path = ROOT) -> str:
    with (root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    if data["project"]["name"] != PROJECT:
        raise ReleaseError(f"pyproject name is {data['project']['name']!r}, expected {PROJECT!r}")
    return data["project"]["version"]


def parse_tag(tag: str) -> str:
    if not tag.startswith("v"):
        raise ReleaseError(f"release tag {tag!r} must start with 'v'")
    version = tag[1:]
    if not VERSION_RE.match(version):
        raise ReleaseError(f"release tag {tag!r} is not a supported PEP 440 version (X.Y[.Z][aN|bN|rcN][.devN])")
    return version


def is_prerelease(version: str) -> bool:
    match = VERSION_RE.match(version)
    if not match:
        raise ReleaseError(f"unsupported version {version!r}")
    return bool(match.group("pre") or match.group("dev"))


def release_title(version: str) -> str:
    match = VERSION_RE.match(version)
    if not match:
        raise ReleaseError(f"unsupported version {version!r}")
    stages = {"a": "alpha", "b": "beta", "rc": "release candidate"}
    label = ""
    if match.group("pre"):
        label = f" ({stages[re.match(r'[a-z]+', match.group('pre')).group(0)]})"
    if match.group("dev"):
        label = " (development)"
    return f"AACP v{version}{label}"


def changelog_section(version: str, text: str) -> str:
    """Return the body of the '## <version>' section, without its heading."""
    heading = re.compile(rf"^## {re.escape(version)}(?:\s|$)")
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if heading.match(line):
            start = index + 1
            break
    if start is None:
        raise ReleaseError(f"CHANGELOG.md has no '## {version}' section; add one before tagging")
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    body = "\n".join(lines[start:end]).strip()
    if not body:
        raise ReleaseError(f"CHANGELOG.md section '## {version}' is empty")
    return body


def expected_files(version: str) -> dict[str, str]:
    return {
        "wheel": f"{DIST_STEM}-{version}-py3-none-any.whl",
        "sdist": f"{DIST_STEM}-{version}.tar.gz",
        "sbom": f"{DIST_STEM}-{version}.cdx.json",
        "checksums": CHECKSUMS,
    }


def metadata(tag: str, root: Path = ROOT, dry_run: bool = False) -> dict:
    """Validate a release tag. dry_run tolerates a missing changelog section (pre-tag rehearsal only)."""
    version = parse_tag(tag)
    declared = project_version(root)
    if declared != version:
        raise ReleaseError(f"tag {tag} does not match pyproject version {declared}")
    if not dry_run:
        changelog_section(version, (root / "CHANGELOG.md").read_text(encoding="utf-8"))
    files = expected_files(version)
    return {
        "tag": tag,
        "version": version,
        "title": release_title(version),
        "prerelease": is_prerelease(version),
        "wheel": files["wheel"],
        "sdist": files["sdist"],
        "sbom": files["sbom"],
        "checksums": files["checksums"],
    }


def render_notes(tag: str, root: Path = ROOT, dry_run: bool = False) -> str:
    meta = metadata(tag, root, dry_run=dry_run)
    version, wheel = meta["version"], meta["wheel"]
    try:
        section = changelog_section(version, (root / "CHANGELOG.md").read_text(encoding="utf-8"))
    except ReleaseError:
        if not dry_run:
            raise
        section = f"_Dry run: CHANGELOG.md has no section for {version} yet._"
    base = f"https://github.com/{REPOSITORY}/releases/download/{tag}"
    stage = "Pre-release (alpha/beta/rc): interfaces may change without notice.\n\n" if meta["prerelease"] else ""
    return f"""{stage}## Install

Python 3.12 or newer. Install the command `aacp` with pipx:

```sh
pipx install {base}/{wheel}
aacp --help
```

Or download `{wheel}` and run `pipx install ./{wheel}`. Without pipx, use
`python -m pip install ./{wheel}` inside a virtual environment.

Runtime dependencies (`jsonschema`, `PyYAML` and their transitive dependencies)
are resolved by pip from the configured package index (PyPI by default). This
release does not bundle them. See `{meta['sbom']}` for the dependency set the
release workflow installed and tested.

## Verify

```sh
sha256sum --check --ignore-missing {CHECKSUMS}        # macOS: shasum -a 256 --check --ignore-missing {CHECKSUMS}
gh attestation verify {wheel} --repo {REPOSITORY}
```

A matching checksum establishes byte identity with what the release workflow
built. A verified attestation establishes that the file was built by this
repository's release workflow from the tagged commit. Neither establishes
correctness, security, independence or any conformance verdict, and this
release grants no certification.

## Assets

| File | Content |
|---|---|
| `{wheel}` | Installable wheel (pure Python) |
| `{meta['sdist']}` | Source distribution |
| `{meta['sbom']}` | CycloneDX SBOM of the tested runtime environment (Linux, CPython 3.12) |
| `{CHECKSUMS}` | SHA-256 of the three files above |

## Changes

{section}
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(dist: Path, out: Path | None = None) -> Path:
    out = out or dist / CHECKSUMS
    files = sorted(p for p in dist.iterdir() if p.is_file() and p.name != CHECKSUMS and p != out)
    if not files:
        raise ReleaseError(f"no files to checksum in {dist}")
    # GNU coreutils format: '<hex>  <name>' (two spaces, text mode), sorted by name.
    out.write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files), encoding="utf-8", newline="\n")
    return out


def verify_checksums(dist: Path, sums: Path | None = None, expected_names: list[str] | None = None) -> dict:
    """Check every line of SHA256SUMS.txt and that the listing names exactly the expected files."""
    sums = sums or dist / CHECKSUMS
    if not sums.is_file():
        raise ReleaseError(f"{sums} is missing")
    listed = {}
    for number, line in enumerate(sums.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._+-]+)", line)
        if not match:
            raise ReleaseError(f"{sums.name}:{number}: malformed line")
        digest, name = match.groups()
        if name in listed:
            raise ReleaseError(f"{sums.name}: {name} listed twice")
        listed[name] = digest
    if expected_names is not None and sorted(listed) != sorted(expected_names):
        raise ReleaseError(f"{sums.name} lists {sorted(listed)}, expected {sorted(expected_names)}")
    for name, digest in listed.items():
        path = dist / name
        if not path.is_file():
            raise ReleaseError(f"{name} is listed in {sums.name} but missing")
        if sha256(path) != digest:
            raise ReleaseError(f"{name}: SHA-256 mismatch")
    return {"verified": sorted(listed)}


def _wheel_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist() if not info.is_dir()}


def _sdist_members(path: Path) -> dict[str, bytes]:
    members = {}
    with tarfile.open(path, "r:gz") as archive:
        for info in archive.getmembers():
            if info.isfile():
                members[info.name] = archive.extractfile(info).read()
            elif not info.isdir():
                raise ReleaseError(f"{path.name}: unexpected non-regular member {info.name}")
    return members


def _check_forbidden(name: str, members) -> None:
    for member in members:
        if member.startswith("/") or ".." in Path(member).parts:
            raise ReleaseError(f"{name}: unsafe member path {member}")
        for part in FORBIDDEN_PARTS:
            if part in member and not member.endswith("runs/README.md"):
                raise ReleaseError(f"{name}: forbidden path {member}")


def check_dist(dist: Path, tag: str, root: Path = ROOT, rebuild: Path | None = None) -> dict:
    meta = metadata(tag, root, dry_run=True)
    version = meta["version"]
    present = sorted(p.name for p in dist.iterdir() if p.is_file())
    wanted = sorted([meta["wheel"], meta["sdist"]])
    if present != wanted:
        raise ReleaseError(f"{dist} must contain exactly {wanted}, found {present}")

    wheel = _wheel_members(dist / meta["wheel"])
    _check_forbidden(meta["wheel"], wheel)
    info = f"{DIST_STEM}-{version}.dist-info"
    meta_text = wheel.get(f"{info}/METADATA", b"").decode("utf-8")
    if f"\nName: {PROJECT}\n" not in meta_text or f"\nVersion: {version}\n" not in meta_text:
        raise ReleaseError("wheel METADATA does not declare the expected name and version")
    if "Requires-Python: >=3.12" not in meta_text:
        raise ReleaseError("wheel METADATA does not declare Requires-Python >=3.12")
    entry_points = wheel.get(f"{info}/entry_points.txt", b"").decode("utf-8")
    if not re.search(r"^aacp\s*=\s*aacp\.cli:main\s*$", entry_points, re.M):
        raise ReleaseError("wheel does not declare the console script aacp = aacp.cli:main")
    if not any(name.startswith(f"{info}/licenses/") and name.endswith("LICENSE") for name in wheel):
        raise ReleaseError("wheel does not include LICENSE")
    for required in ("aacp/__init__.py", "aacp/cli.py", "conformance/lab/__init__.py"):
        if required not in wheel:
            raise ReleaseError(f"wheel is missing {required}")
    schemas = sorted(p.name for p in (root / "schema").glob("*.json"))
    packaged = sorted(Path(n).name for n in wheel if n.startswith("aacp/schemas/") and n.endswith(".json"))
    if schemas != packaged:
        raise ReleaseError(f"wheel schemas {packaged} differ from schema/*.json {schemas}")
    for name in packaged:
        if wheel[f"aacp/schemas/{name}"] != (root / "schema" / name).read_bytes():
            raise ReleaseError(f"wheel schema {name} differs from the committed schema")

    sdist = _sdist_members(dist / meta["sdist"])
    _check_forbidden(meta["sdist"], sdist)
    prefix = f"{DIST_STEM}-{version}/"
    if any(not name.startswith(prefix) for name in sdist):
        raise ReleaseError(f"sdist members must live under {prefix}")
    for required in ("pyproject.toml", "LICENSE", "README.md", "PKG-INFO", "aacp/cli.py"):
        if prefix + required not in sdist:
            raise ReleaseError(f"sdist is missing {required}")
    if sdist[prefix + "pyproject.toml"] != (root / "pyproject.toml").read_bytes():
        raise ReleaseError("sdist pyproject.toml differs from the committed file")

    result = {"version": version, "wheel_sha256": sha256(dist / meta["wheel"]),
              "wheel_members": len(wheel), "sdist_members": len(sdist)}
    if rebuild is not None:
        # The wheel must be byte-reproducible under SOURCE_DATE_EPOCH. gzip/tar headers of the
        # sdist are not, so the sdist is compared member by member instead.
        if sha256(rebuild / meta["wheel"]) != result["wheel_sha256"]:
            raise ReleaseError("wheel is not byte-reproducible: an independent rebuild differs")
        if _sdist_members(rebuild / meta["sdist"]) != sdist:
            raise ReleaseError("sdist content is not reproducible: an independent rebuild differs")
        result["reproducible"] = True
    return result


def stamp_sbom_serial(dist: Path, tag: str) -> dict:
    """Give the SBOM a deterministic ``serialNumber``.

    ``cyclonedx-py --output-reproducible`` omits ``serialNumber``, and
    actions/attest refuses a CycloneDX document without one ("Unsupported SBOM
    format"). A random UUID would break reproducibility, so the serial is a
    UUIDv5 of the version and the wheel's SHA-256: the same wheel always gets
    the same serial, and a different wheel a different one.
    """
    version = parse_tag(tag)
    files = expected_files(version)
    path = dist / files["sbom"]
    try:
        bom = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ReleaseError(f"cannot read SBOM {path.name}: {error}") from error
    if bom.get("bomFormat") != "CycloneDX" or not bom.get("specVersion"):
        raise ReleaseError(f"{path.name} is not a CycloneDX document")
    wheel = sha256(dist / files["wheel"])
    serial = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"aacp-conformance/{version}/sha256:{wheel}"))
    if bom.get("serialNumber") not in (None, serial):
        raise ReleaseError(f"{path.name} already has another serialNumber {bom['serialNumber']!r}")
    bom["serialNumber"] = serial
    path.write_text(json.dumps(bom, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"sbom": files["sbom"], "serialNumber": serial}


def _write_github_output(path: str, values: dict) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            text = json.dumps(value) if isinstance(value, bool) else str(value)
            if "\n" in text:
                raise ReleaseError(f"output {key} must be a single line")
            handle.write(f"{key}={text}\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("metadata", help="validate tag, version and changelog")
    p.add_argument("--tag", required=True)
    p.add_argument("--github-output")
    p.add_argument("--dry-run", action="store_true", help="tolerate a missing changelog section")
    p = commands.add_parser("notes", help="render release notes")
    p.add_argument("--tag", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true", help="tolerate a missing changelog section")
    p = commands.add_parser("check-dist", help="check built distributions")
    p.add_argument("--dist", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--rebuild-dist")
    p = commands.add_parser("sbom-serial", help="give the SBOM a deterministic serialNumber")
    p.add_argument("--dist", required=True)
    p.add_argument("--tag", required=True)
    p = commands.add_parser("checksums", help="write SHA256SUMS.txt")
    p.add_argument("--dist", required=True)
    p.add_argument("--out")
    p = commands.add_parser("verify-checksums", help="verify SHA256SUMS.txt against the release asset set")
    p.add_argument("--dist", required=True)
    p.add_argument("--tag", help="also require exactly the asset set for this tag")
    args = parser.parse_args(argv)
    try:
        if args.command == "metadata":
            result = metadata(args.tag, dry_run=args.dry_run)
            if args.github_output:
                _write_github_output(args.github_output, result)
        elif args.command == "notes":
            Path(args.out).write_text(render_notes(args.tag, dry_run=args.dry_run), encoding="utf-8", newline="\n")
            result = {"notes": args.out}
        elif args.command == "check-dist":
            result = check_dist(Path(args.dist), args.tag,
                                rebuild=Path(args.rebuild_dist) if args.rebuild_dist else None)
        elif args.command == "sbom-serial":
            result = stamp_sbom_serial(Path(args.dist), args.tag)
        elif args.command == "verify-checksums":
            names = None
            if args.tag:
                files = expected_files(parse_tag(args.tag))
                names = [files["wheel"], files["sdist"], files["sbom"]]
            result = verify_checksums(Path(args.dist), expected_names=names)
        else:
            result = {"checksums": str(write_checksums(Path(args.dist), Path(args.out) if args.out else None))}
    except ReleaseError as error:
        print(f"release: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
