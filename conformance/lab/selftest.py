"""Negative runner self-test (the E030 failure mode, after imokokok's review in #177).

A wrapper that keeps going after a failed verifier can print a success line and exit 0
with no new results. This builds a throw-away manual verification run whose verifier
fails after every pin check has passed, runs it, and reports three facts separately:

- nonzero_exit: the process exited nonzero;
- no_results_written: no results/claims.json was written;
- no_success_line: the success line ("measured") was not printed.

Collapsing them into one boolean is the same class of defect, so they stay separate.
Standard library only; works from a vendored package. No network: the subject is a
local repository reached through a git URL rewrite that is set only for the child.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

LAB_PARENT = Path(__file__).resolve().parents[2]  # the directory that contains conformance/
SUBJECT_URL = "https://selftest.invalid/subject"
REF = "https://selftest.invalid/issues/1"
SUCCESS_LINE = "measured"
FAILING_VERIFIER = '''"""Self-test verifier: fails after every pin check has passed."""

raise RuntimeError("verifier failed on purpose (runner self-test)")


def claim(doc, context):
    return {"result": "ESTABLISHED", "reads": ["value"]}
'''


def _git(*args, cwd, env):
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)


def _env(tmp):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    env.update({
        "GIT_AUTHOR_NAME": "selftest", "GIT_AUTHOR_EMAIL": "selftest@selftest.invalid",
        "GIT_COMMITTER_NAME": "selftest", "GIT_COMMITTER_EMAIL": "selftest@selftest.invalid",
        "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{(tmp / 'remotes').as_posix()}/.insteadOf",
        "GIT_CONFIG_VALUE_0": "https://selftest.invalid/",
        "PYTHONPATH": str(LAB_PARENT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return env


def _build(tmp, env):
    """A frozen manual verification run named 'selftest' under tmp/runs."""
    subject = tmp / "remotes" / "subject"
    subject.mkdir(parents=True)
    _git("init", "--quiet", "-b", "main", cwd=subject, env=env)
    data = b'{"value": 1}\n'
    (subject / "input.json").write_bytes(data)
    _git("add", "-A", cwd=subject, env=env)
    _git("commit", "--quiet", "-m", "selftest subject", cwd=subject, env=env)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=subject, env=env, check=True,
                            capture_output=True, text=True).stdout.strip()
    run = tmp / "runs" / "selftest"
    (run / "verifier").mkdir(parents=True)
    (run / "verifier" / "failing.py").write_text(FAILING_VERIFIER, encoding="utf-8")
    scope = {
        "lab_version": "0.3", "run_id": "selftest", "kind": "verification",
        "agreement_ref": REF, "independence": "SELF_RUN",
        "runner": {"project": "runner self-test", "maintainers": ["selftest"]},
        "agreement_parties": ["selftest"],
        "subjects": [{"project": "self-test subject", "maintainers": ["selftest"], "repo": SUBJECT_URL,
                      "commit": commit, "paths": ["input.json"],
                      "files_sha256": {"input.json": hashlib.sha256(data).hexdigest()},
                      "license": "Apache-2.0", "attribution": "runner self-test"}],
        "claim_ceiling": {"establishes": ["runner failure propagation only"],
                          "does_not_establish": ["anything about any subject"]},
        "publication": {"private_first": True, "approvers": ["selftest"], "unreleased_citable": False},
        "inputs": [{"id": "input", "subject": 0, "path": "input.json"}],
        "claims": [{"id": "claim", "text": "self-test claim", "layer": "selftest", "check": "failing:claim",
                    "reads_fields": ["value"], "inputs": ["input"]}],
        "reference_time": None,
    }
    (run / "SCOPE.json").write_text(json.dumps(scope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (tmp / "lab.toml").write_text('runs_dir = "runs"\n', encoding="utf-8")
    steps = [["consent", "selftest", "--who", "selftest", "--action", a, "--ref", REF]
             for a in ("scope_agreed", "run_authorized")]
    steps += [["freeze", "selftest"], ["freeze", "selftest", "--published-ref", REF],
              ["admit", "selftest", "--input", "input", "--decision", "ADMITTED", "--rationale", "selftest",
               "--who", "selftest", "--ref", REF]]
    init = subprocess.run([sys.executable, "-c",
                           "from pathlib import Path; from conformance.lab import state;"
                           "from conformance.lab.canonical import write_json;"
                           "write_json(Path('runs/selftest/CONSENT.json'), {'events': []});"
                           "state.new_state(Path('runs/selftest'), '2026-01-01T00:00:00Z')"],
                          cwd=tmp, env=env, capture_output=True, text=True)
    if init.returncode != 0:
        raise RuntimeError(f"self-test setup failed: {init.stderr.strip()}")
    for step in steps:
        done = subprocess.run([sys.executable, "-m", "conformance.lab", *step], cwd=tmp, env=env,
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError(f"self-test setup step {step[0]} failed: {done.stderr.strip()}")
    return run


def run_selftest(command=None, workdir=None):
    """Run the failing run through `command` (default: the lab CLI) and report the three facts."""
    with tempfile.TemporaryDirectory(prefix="aac-selftest-", dir=workdir) as name:
        tmp = Path(name)
        env = _env(tmp)
        run = _build(tmp, env)
        argv = command or [sys.executable, "-m", "conformance.lab", "run", "selftest"]
        done = subprocess.run(argv, cwd=tmp, env=env, capture_output=True, text=True)
        lines = [line.strip() for line in done.stdout.splitlines()]
        return {"nonzero_exit": done.returncode != 0,
                "no_results_written": not (run / "results" / "claims.json").exists(),
                "no_success_line": SUCCESS_LINE not in lines}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Negative runner self-test (three separate assertions).")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_selftest()
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        for key, value in result.items():
            print(f"{key}: {'yes' if value else 'NO'}")
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
