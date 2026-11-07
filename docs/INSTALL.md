# Install AACP from a GitHub Release

AACP is distributed as versioned assets on this repository's
[GitHub Releases](https://github.com/darklordVirtual/agent-authority-conformance/releases).
It is not published on PyPI. The installer name is `aacp-conformance`; the
command is `aacp`. Python 3.12 or newer.

## Install

```sh
pipx install https://github.com/darklordVirtual/agent-authority-conformance/releases/download/v0.3.0a1/aacp_conformance-0.3.0a1-py3-none-any.whl
aacp --help
```

Replace `v0.3.0a1` with the release you want. From a downloaded file, use
`pipx install ./aacp_conformance-0.3.0a1-py3-none-any.whl`. Without pipx,
install into a virtual environment:

```sh
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
python -m pip install ./aacp_conformance-0.3.0a1-py3-none-any.whl
```

Then follow [CLI onboarding](CLI-ONBOARDING.md).

## Verify before installing

Each release carries:

| Asset | Purpose |
|---|---|
| `aacp_conformance-<version>-py3-none-any.whl` | Installable wheel |
| `aacp_conformance-<version>.tar.gz` | Source distribution |
| `aacp_conformance-<version>.cdx.json` | CycloneDX SBOM of the runtime environment the release workflow installed and tested |
| `SHA256SUMS.txt` | SHA-256 of the three files above |

```sh
gh release download v0.3.0a1 --repo darklordVirtual/agent-authority-conformance
sha256sum --check SHA256SUMS.txt                 # macOS: shasum -a 256 --check SHA256SUMS.txt
gh attestation verify aacp_conformance-0.3.0a1-py3-none-any.whl \
  --repo darklordVirtual/agent-authority-conformance
gh attestation verify aacp_conformance-0.3.0a1-py3-none-any.whl \
  --repo darklordVirtual/agent-authority-conformance \
  --predicate-type https://cyclonedx.org/bom
```

What each check establishes:

- **Checksum match**: the file is byte-identical to what the release workflow
  built. It says nothing about who built it if the checksum file came from the
  same place as the file.
- **Provenance attestation**: the file was built by this repository's
  `.github/workflows/release.yml` from the tagged commit, signed through
  Sigstore with a short-lived GitHub Actions identity.
- **SBOM attestation**: the SBOM was produced for this exact wheel by the same
  workflow.

None of them establishes correctness, security, independence or any
conformance verdict. A release grants no certification.

## Dependencies and offline installs

The wheel is pure Python. Its runtime dependencies (`jsonschema`, `PyYAML` and
their transitive dependencies, including the compiled `rpds-py`) are resolved
by pip from the configured package index, PyPI by default. That is ordinary
package installation; the release does not bundle them.

To install without reaching PyPI at install time, prepare a wheelhouse on a
connected machine with the same OS, architecture and Python version, carry it
over and install from it:

```sh
python -m pip download --dest wheelhouse ./aacp_conformance-0.3.0a1-py3-none-any.whl
python -m pip install --no-index --find-links wheelhouse aacp-conformance==0.3.0a1
```

The SBOM records the dependency versions the release was tested with on Linux
and CPython 3.12; pip may resolve newer compatible versions of the unpinned
transitive dependencies at your install time.

## Pre-releases

Versions with an `a`, `b` or `rc` suffix are GitHub pre-releases. Their
interfaces, result shapes and profiles may change without a migration path.
