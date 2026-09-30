"""python -m conformance.lab: run protocol commands (see RUN-PROTOCOL-v0.3.md)."""

import argparse
import subprocess
import sys
from pathlib import Path

from . import consent, lifecycle, runner
from .canonical import utc_now
from .config import load_config
from .errors import LabError
from .state import load_state


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
    p.add_argument("--action", required=True, choices=sorted(consent.ACTIONS))
    p.add_argument("--ref", required=True)
    p = sub.add_parser("freeze", help="write the plan and print its hash; then record where it was published")
    p.add_argument("run_id")
    p.add_argument("--published-ref")
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
    return parser


def main(argv=None, config=None):
    args = build_parser().parse_args(argv)
    cfg = config or load_config()
    runs, now = Path(cfg["runs_dir"]), utc_now()
    run_dir = runs / args.run_id if getattr(args, "run_id", None) else None
    try:
        if args.command == "init":
            print(lifecycle.init(runs, args.run_id, args.kind, now, args.template, args.follow_up, args.commit))
        elif args.command == "pin":
            lifecycle.pin(run_dir)
            print("pinned; review SCOPE.json and ask the parties to agree it")
        elif args.command == "consent":
            consent.add(run_dir, args.who, args.action, args.ref, now)
            print(f"recorded {args.action} by {args.who}")
        elif args.command == "freeze":
            digest, frozen = lifecycle.freeze(run_dir, now, args.published_ref)
            print(f"plan sha256: {digest}")
            if not frozen:
                print("Publish this hash (commit or issue comment), then: freeze --published-ref <URL>")
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
        elif args.command == "rerun":
            return subprocess.run([sys.executable, "-B", str(args.package / "rerun.py")]).returncode
    except LabError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
