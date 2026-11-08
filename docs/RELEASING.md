# Releasing AACP

Releases are built and published only by `.github/workflows/release.yml`. A
maintainer prepares the version and changelog, pushes an annotated tag, and
approves the publish step. Nobody uploads assets by hand.

## One-time repository setup

These are repository settings; the workflow cannot create them safely itself.

1. **`release` environment** (Settings → Environments → New environment →
   `release`): add a required reviewer, enable "Prevent self-review" if more
   than one maintainer exists, and restrict deployment tags to `v*`. If this
   environment does not exist, GitHub creates it on first use **without
   protection**, and publication would not wait for approval.
2. **Tag protection** (Settings → Rules → Rulesets → New tag ruleset): target
   `v*`, restrict creation, update and deletion to maintainers.
3. **Immutable releases** (Settings → General → Releases): enable, so a
   published release's assets and tag cannot be changed or replaced. The
   workflow creates a draft, uploads every asset and only then publishes,
   which is what immutable releases require.
4. Artifact attestations need a public repository on Free, Pro or Team plans.

## Cut a release

1. On a branch, set `version` in `pyproject.toml` (PEP 440: `0.3.0a1`,
   `0.3.0b1`, `0.3.0rc1`, `0.3.0`), and give `CHANGELOG.md` a section headed
   `## <version>` with what the release contains. Merge to `main` after
   review. Pull requests that touch release inputs rehearse the build, the
   distribution checks and the installed-CLI matrix without publishing.
2. Optionally rehearse on `main`: Actions → Release → Run workflow. This runs
   every step except publication, including the full conformance suite.
3. Locally, check the gates before tagging:

   ```sh
   git switch main && git pull --ff-only
   python scripts/release.py metadata --tag v0.3.0a1
   python scripts/release.py notes --tag v0.3.0a1 --out /tmp/notes.md   # read it
   ```

4. Tag the reviewed commit on `main` and push the tag:

   ```sh
   git tag -a v0.3.0a1 -m "AACP 0.3.0a1"
   git push origin v0.3.0a1
   ```

5. Watch the run. When `verify`, `build` and `smoke` are green, review the
   `release-dist` artifact and the checksum summary, then approve the
   `release` environment deployment. The `publish` job attests provenance and
   SBOM, creates a draft release with all assets, checks the uploaded asset
   list, and publishes.
6. Verify the published release as a user would, following
   [INSTALL.md](INSTALL.md#verify-before-installing).

## What the workflow checks

| Job | Gate |
|---|---|
| `verify` | Tag is `v` + the `pyproject.toml` version, the changelog has a non-empty section for it, the tagged commit is on `main`, and the full conformance suite, reference vectors and lab tests pass without rewriting tracked files |
| `build` | `python -m build` twice with `SOURCE_DATE_EPOCH` from the commit; the wheel must be byte-identical and the sdist content-identical; the wheel declares name, version, `Requires-Python >=3.12`, the `aacp` console script and LICENSE, packages every `schema/*.json` byte for byte, and contains no `runs/`, `.github/` or cache paths; `twine check --strict`; CycloneDX SBOM from a pip-less environment holding only the wheel and its dependencies; `SHA256SUMS.txt` |
| `smoke` | On Linux, macOS and Windows with Python 3.12 and 3.13 (plus the sdist on Linux): checksums verify, the artifact installs into a fresh virtual environment, and `aacp init`, `validate`, `inspect` and `adversarial --list` run in an empty directory outside any checkout with the expected `NOT_RUN` results. The assertions import `aacp` in isolated mode and fail if it resolves anywhere but the test environment |
| `publish` | Only on a tag push and after environment approval: checksums re-verified, refuses an existing release, Sigstore-signed build provenance for all assets and an SBOM attestation for the wheel, draft → upload → asset-list check → publish |

All third-party actions are pinned to full commit SHAs. Build tooling is
pinned in `requirements-release.txt`.

## When something is wrong

- **A gate fails before `publish`**: nothing has been published. Fix on a
  branch, merge, delete the tag (`git push origin :refs/tags/v0.3.0a1`,
  `git tag -d v0.3.0a1`) and tag the fixed commit.
- **A published release is wrong**: do not replace it. Publish a new version
  (`0.3.0a2`) and say in its changelog what was wrong with the previous one.
  With immutable releases the old assets cannot be changed anyway.
- **The `publish` job failed after creating a draft**: delete the draft
  release in the GitHub UI and re-run the failed job.

## Not done here

- No PyPI publication. A PyPI release would need trusted publishing and an
  explicit decision.
- Runtime dependencies are not bundled; see
  [INSTALL.md](INSTALL.md#dependencies-and-offline-installs).
- A reusable `uses: darklordVirtual/agent-authority-conformance@v1` GitHub
  Action does not exist yet.
