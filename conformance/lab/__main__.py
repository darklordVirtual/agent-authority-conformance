"""python -m conformance.lab: run protocol commands (see RUN-PROTOCOL-v0.3.md)."""

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from . import consent, lifecycle, runner
from .canonical import read_json, utc_now, write_json
from .config import load_config
from .errors import LabError
from .state import load_state


def _provenance(p):
    p.add_argument("--drafted-by", default="human", metavar="human|agent:<id>",
                   help="who drafted the linked statement; disclosure only")
    p.add_argument("--ai-assisted", action="store_true")
    p.add_argument("--recorded-by", help="handle operating this tool, when not --who")


def _provenance_args(args):
    return {"drafted_by": args.drafted_by, "ai_assisted": args.ai_assisted, "recorded_by": args.recorded_by}


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m conformance.lab", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="create runs/<run_id> in state SCOPED")
    p.add_argument("run_id")
    p.add_argument("--kind", choices=("adequacy", "verification"))
    p.add_argument("--template", type=Path)
    p.add_argument("--follow-up", help="previous run_id to follow up at a new commit")
    p.add_argument("--commit")
    for name, text in (("pin", "fill files_sha256 from the pinned commits"),
                       ("run", "execute the frozen plan"),
                       ("package", "build the delivery package"),
                       ("publish", "make the private repository public once every approver approved"),
                       ("withhold", "record a declined publication"),
                       ("status", "print the lifecycle state")):
        sub.add_parser(name, help=text).add_argument("run_id")
    p = sub.add_parser("consent", help="append a consent event")
    p.add_argument("run_id")
    p.add_argument("--who", required=True)
    p.add_argument("--action", required=True, choices=sorted(consent.ACTIONS - {"admission"}))
    p.add_argument("--ref", required=True)
    p.add_argument("--condition", action="append", metavar="CLAIM[,CLAIM]=TEXT",
                   help="scope_agreed only: a condition on the named claims (repeatable)")
    _provenance(p)
    p = sub.add_parser("admit", help="record an admission decision for one input (manual track)")
    p.add_argument("run_id")
    p.add_argument("--input", required=True)
    p.add_argument("--decision", required=True, choices=consent.DECISIONS)
    p.add_argument("--rationale", required=True)
    p.add_argument("--who", required=True)
    p.add_argument("--ref", required=True)
    _provenance(p)
    p = sub.add_parser("freeze", help="write the plan and print its hash; then record where it was published")
    p.add_argument("run_id")
    p.add_argument("--published-ref")
    p.add_argument("--not-preregistered", action="store_true",
                   help="self-service only: freeze without publishing the plan hash first (reported)")
    p = sub.add_parser("share", help="create a private repository and invite read-only reviewers")
    p.add_argument("run_id")
    p.add_argument("--org")
    p.add_argument("--invite", nargs="*", default=[])
    p = sub.add_parser("review", help="record factual corrections or survivor classification")
    p.add_argument("run_id")
    p.add_argument("--who", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--corrections", metavar="URL")
    group.add_argument("--classification", metavar="URL")
    p = sub.add_parser("rerun", help="rerun a package with its own vendored lab code")
    p.add_argument("package", type=Path)
    p = sub.add_parser("selftest", help="negative runner self-test: nonzero exit, no results, no success line")
    p.add_argument("--json", action="store_true")
    return parser


CAPTURE_FILE = "RUN-CAPTURE.json"


def _procedure_revision():
    """The lab checkout that executed, when it is a git checkout: commit and whether
    tracked files were modified. A vendored package copy reports 'vendored'."""
    root = Path(__file__).resolve().parents[2]
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0 or not (root / ".git").exists():
        return {"source": "vendored"}
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no", "--",
                            "conformance/lab"], capture_output=True, text=True).stdout.strip() != ""
    return {"source": "git", "commit": head.stdout.strip(), "lab_modified": dirty}


def _capture(run_dir, argv, started, code, error):
    """Append one run attempt, as it happened, to RUN-CAPTURE.json in the run directory.
    Arguments are kept as given (run ids and flags); absolute paths are not recorded."""
    if run_dir is None or not (run_dir / "STATE.json").is_file():
        return
    path = run_dir / CAPTURE_FILE
    doc = read_json(path) if path.is_file() else {
        "note": "Every run attempt with its arguments, start and end time and exit status.", "attempts": []}
    safe = [a if not Path(a).is_absolute() else "<absolute path omitted>" for a in argv]
    workspace = run_dir.resolve().parent.parent  # the directory holding runs/
    try:
        cwd = Path.cwd().resolve().relative_to(workspace).as_posix()
    except ValueError:
        cwd = "<outside the lab workspace>"
    entry = {"argv": safe, "cwd_relative_to_workspace": cwd, "procedure_revision": _procedure_revision(),
             "started_at": started, "ended_at": utc_now(), "exit_status": code,
             "python": platform.python_version(), "platform": platform.system()}
    if error:
        entry["error"] = error
    doc["attempts"].append(entry)
    write_json(path, doc)


def main(argv=None, config=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = build_parser().parse_args(argv)
    cfg = config or load_config()
    runs = Path(cfg["runs_dir"])
    run_dir = runs / args.run_id if getattr(args, "run_id", None) else None
    if args.command != "run":
        return _dispatch(args, cfg, runs, run_dir)
    started, error, code = utc_now(), None, None
    try:
        code = _dispatch(args, cfg, runs, run_dir, capture_error=True)
    except _Failed as failed:
        code, error = failed.code, failed.message
    finally:
        _capture(run_dir, argv, started, 1 if code is None else code, error)
    return code


class _Failed(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def _dispatch(args, cfg, runs, run_dir, capture_error=False):
    now = utc_now()
    try:
        if args.command == "init":
            print(lifecycle.init(runs, args.run_id, args.kind, now, args.template, args.follow_up, args.commit))
        elif args.command == "pin":
            lifecycle.pin(run_dir)
            print("pinned; review SCOPE.json and ask the parties to agree it")
        elif args.command == "consent":
            conditions = [consent.parse_condition(c) for c in args.condition] if args.condition else None
            consent.add(run_dir, args.who, args.action, args.ref, now, conditions=conditions,
                        **_provenance_args(args))
            print(f"recorded {args.action} by {args.who}")
        elif args.command == "admit":
            consent.add(run_dir, args.who, "admission", args.ref, now, input=args.input,
                        decision=args.decision, rationale=args.rationale, **_provenance_args(args))
            print(f"recorded admission of {args.input}: {args.decision} by {args.who}")
        elif args.command == "freeze":
            digest, frozen = lifecycle.freeze(run_dir, now, args.published_ref,
                                              not_preregistered=args.not_preregistered)
            print(f"plan sha256: {digest}")
            if not frozen:
                print("Publish this hash (commit or issue comment), then: freeze --published-ref <URL>"
                      " (self-service runs may instead pass --not-preregistered)")
        elif args.command == "run":
            results = runner.run(run_dir, now)
            if runner.has_survivors(results):
                print("measured; survivors present (corpus discrimination limits)")
                return 1
            print("measured")
        elif args.command == "package":
            lifecycle.package(run_dir, now)
            print(f"packaged {run_dir}")
        elif args.command == "share":
            print(lifecycle.share(run_dir, args.org or cfg["org"], args.invite, now))
        elif args.command == "review":
            kind = "corrections" if args.corrections else "classification"
            lifecycle.review(run_dir, args.who, kind, args.corrections or args.classification, now)
            print("recorded review")
        elif args.command == "publish":
            lifecycle.publish(run_dir, now)
            print("published")
        elif args.command == "withhold":
            lifecycle.withhold(run_dir, now)
            print("withheld")
        elif args.command == "status":
            print(load_state(run_dir)["state"])
        elif args.command == "selftest":
            from .selftest import main as selftest_main
            return selftest_main(["--json"] if args.json else [])
        elif args.command == "rerun":
            return subprocess.run([sys.executable, "-B", str(args.package / "rerun.py")]).returncode
    except LabError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if capture_error:
            raise _Failed(exc.exit_code, str(exc)) from exc
        return exc.exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
