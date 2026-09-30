#!/usr/bin/env python3
"""Stand-in for gh in tests: logs calls and keeps repository state in JSON."""
import json
import os
import subprocess
import sys
from pathlib import Path

state_path = Path(os.environ["FAKE_GH_STATE"])
state = json.loads(state_path.read_text()) if state_path.exists() else {"owners": {}, "repos": {}, "calls": []}
args = sys.argv[1:]
state["calls"].append(args)


def done(output=None, code=0):
    state_path.write_text(json.dumps(state))
    if output is not None:
        print(output)
    raise SystemExit(code)


if os.environ.get("FAKE_GH_FAIL") and os.environ["FAKE_GH_FAIL"] in args:
    print("simulated failure", file=sys.stderr)
    done(code=1)
if args[:1] == ["api"] and args[1].startswith("users/"):
    done(state["owners"].get(args[1][len("users/"):], "User"))
if args[:2] == ["repo", "view"]:
    repo = state["repos"].get(args[2])
    if repo is None:
        print("not found", file=sys.stderr)
        done(code=1)
    done(repo["visibility"])
if args[:2] == ["repo", "create"]:
    state["repos"][args[2]] = {"visibility": "PRIVATE" if "--private" in args else "PUBLIC", "collaborators": {}}
    bare = Path(os.environ["AAC_GIT_REMOTE_BASE"]) / f"{args[2]}.git"
    subprocess.run(["git", "init", "--quiet", "--bare", "-b", "main", str(bare)], check=True)
    done()
if args[:2] == ["repo", "edit"]:
    state["repos"][args[2]]["visibility"] = args[args.index("--visibility") + 1].upper()
    done()
if args[:1] == ["api"] and "-X" in args:
    _, owner, repo, _, user = next(a for a in args if a.startswith("repos/")).split("/")
    permission = next(a for a in args if a.startswith("permission=")).split("=", 1)[1]
    state["repos"][f"{owner}/{repo}"]["collaborators"][user] = permission
    done()
print(f"unhandled: {args}", file=sys.stderr)
done(code=1)
