"""Install one built AACP distribution into a fresh virtual environment and exercise
the installed `aacp` command from an empty directory outside any checkout.

    python scripts/smoke_installed_cli.py dist/aacp_conformance-0.3.0a1-py3-none-any.whl --version 0.3.0a1

Standard library only, cross-platform. The assertions run in the virtual
environment's interpreter in isolated mode (-I), so the checkout is never on
sys.path and only the installed package is tested. Exit status 0 means the
installed CLI behaved as below; it is not a property verdict.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv

CHECK = r"""
import json, sys
from importlib.metadata import version
from pathlib import Path
import aacp
from aacp.cli import validator

expected, venv_root = sys.argv[1], Path(sys.argv[2]).resolve()
assert version("aacp-conformance") == expected, (version("aacp-conformance"), expected)
location = Path(aacp.__file__).resolve()
assert venv_root in location.parents, f"aacp imported from {location}, not from the test environment"
for name in ("init", "validate", "inspect"):
    result = json.loads(Path(f"{name}.json").read_text(encoding="utf-8"))
    validator("aacp-command-result-v1.schema.json").validate(result)
    assert result["status"] == "OK", (name, result["status"])
    assert result["verification_status"] == "NOT_RUN", (name, result["verification_status"])
    assert result["property_verdict"] is None, (name, result["property_verdict"])
vectors = json.loads(Path("adversarial-vectors.json").read_text(encoding="utf-8"))
assert vectors["suite_version"] == "aacp-portable-cfg-adversarial-v1", vectors["suite_version"]
assert {row["property"] for row in vectors["cases"]} == {"C", "F", "G"}
assert all("challenge" in row for row in vectors["cases"])
validator("aacp-adversarial-run-v1.schema.json")
print(json.dumps({"installed": expected, "location": str(location), "checks": "OK"}))
"""


def run(command, *, cwd=None, stdout=None, env=None):
    shown = (str(part) if "\n" not in str(part) else "<inline check>" for part in command)
    print("+ " + " ".join(shown), file=sys.stderr, flush=True)
    subprocess.run([str(part) for part in command], cwd=cwd, stdout=stdout, env=env, check=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("artifact", help="path to a built wheel or sdist")
    parser.add_argument("--version", required=True, help="expected installed version")
    parser.add_argument("--keep", action="store_true", help="keep the temporary directory")
    args = parser.parse_args(argv)

    artifact = Path(args.artifact).resolve()
    if not artifact.is_file():
        parser.error(f"{artifact} does not exist")
    work = Path(tempfile.mkdtemp(prefix="aacp-smoke-"))
    try:
        env_dir = work / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
        scripts = env_dir / ("Scripts" if os.name == "nt" else "bin")
        suffix = ".exe" if os.name == "nt" else ""
        python, cli = scripts / f"python{suffix}", scripts / f"aacp{suffix}"
        # Keep the caller's environment from leaking a checkout onto sys.path.
        clean_env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV")}
        run([python, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", artifact], env=clean_env)

        subject = work / "subject"
        subject.mkdir()
        run([cli, "--help"], cwd=subject, stdout=subprocess.DEVNULL, env=clean_env)
        for name, command in (
            ("init", ["init", "--name", "package-smoke", "--json"]),
            ("validate", ["validate", "--json"]),
            ("inspect", ["inspect", "--json"]),
            ("adversarial-vectors", ["adversarial", "--list", "--json"]),
        ):
            with (subject / f"{name}.json").open("wb") as handle:
                run([cli, *command], cwd=subject, stdout=handle, env=clean_env)
        run([python, "-I", "-c", CHECK, args.version, env_dir], cwd=subject, env=clean_env)
    finally:
        if args.keep:
            print(f"kept {work}", file=sys.stderr)
        else:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
