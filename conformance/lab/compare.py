"""compare: two runs of the same bounded claims, side by side.

Different tools and runners may establish different bounded facts, and disagreement
is itself evidence. This lists each (input, claim) row from both runs next to each
other with each run's provenance. It never combines them: no score, no count of
matching rows, no majority. Standard library only.
"""

from pathlib import Path

from .canonical import read_json
from .errors import ScopeError
from .independence import FEDERATION

NOTE = ("Side-by-side listing of two runs. It is not a verdict, not a combined result and not "
        "independent evidence by itself; each run keeps its own claim ceiling, independence label "
        "and publication status.")


def _load(run_dir):
    run_dir = Path(run_dir)
    scope = read_json(run_dir / "SCOPE.json")
    if scope.get("kind") != "verification":
        raise ScopeError(f"{run_dir}: compare supports verification runs")
    records = read_json(run_dir / "results" / "claims.json")["records"]
    state = read_json(run_dir / "STATE.json") if (run_dir / "STATE.json").is_file() else {}
    return scope, records, state


def compare_runs(a, b):
    runs, rows = [], {}
    pins = []
    for side, run_dir in (("a", a), ("b", b)):
        scope, records, state = _load(run_dir)
        runs.append({"side": side, "run_id": scope["run_id"], "track": scope.get("track", "manual"),
                     "runner": scope["runner"]["project"], "independence": scope["independence"],
                     "federation_label": FEDERATION[scope["independence"]],
                     "procedure": scope.get("procedure"), "state": state.get("state"),
                     "plan_sha256": state.get("plan_sha256")})
        pins.append([{"repo": s["repo"], "commit": s["commit"], "files_sha256": s["files_sha256"]}
                     for s in scope["subjects"]])
        for r in records:
            rows.setdefault((r["input"], r["claim"]), {})[side] = r["result"] or r["execution"]
    return {"note": NOTE, "runs": runs, "same_pinned_inputs": pins[0] == pins[1],
            "rows": [{"input": i, "claim": c, "a": v.get("a"), "b": v.get("b")}
                     for (i, c), v in sorted(rows.items())]}
