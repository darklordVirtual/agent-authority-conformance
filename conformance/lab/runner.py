"""run: execute a frozen plan and write results (RUN-PROTOCOL-v0.3 §4)."""

import tempfile
from pathlib import Path

from . import pins, plan, state
from .canonical import read_json, sha256_file, write_json
from .engines.base import get_engine, identity_for
from .errors import PlanError
from .kinds import adequacy, verification
from .scope import load_scope


def execute(run_dir, scope, trees):
    """Run every row or claim. Returns {relative path: JSON object}; writes nothing."""
    out = {}
    if scope["kind"] == "verification":
        records = verification.execute(run_dir, scope, trees)
        out["results/claims.json"] = {"records": records}
        agree = verification.agreement(run_dir, records)
        if agree is not None:
            out["results/agreement.json"] = agree
        return out
    tree = trees[0]
    adequacy.prepare_tree(run_dir, tree)
    primary = get_engine(scope["engine"])
    cross = scope["engine"].get("cross_check")
    for row in scope["rows"]:
        result, report = adequacy.execute_row(run_dir, scope, tree, row, primary)
        out[f"results/{row['id']}.json"] = result
        if report is not None:
            original = report.pop("original_text", None)
            out[f"results/engine/{row['id']}.json"] = report
            if original is not None:
                out[f".local/engine/{row['id']}.original.json"] = original
        if cross:
            second, _ = adequacy.execute_row(run_dir, scope, tree, row,
                                             get_engine({**scope["engine"], "name": cross}))
            a = {m["fault_id"]: m["outcome"] for m in result["mutants"]}
            b = {m["fault_id"]: m["outcome"] for m in second["mutants"]}
            out[f"results/cross-check/{row['id']}.json"] = {
                "note": "Engine agreement only. It never changes the subject's row result.",
                "primary": primary.name, "secondary": cross,
                "disagreements": [{"fault_id": f, "primary": a[f], "secondary": b.get(f)}
                                  for f in sorted(a) if a[f] != b.get(f)],
            }
        # Pinned bytes must be unchanged after every row, cross-check included.
        pins.verify(tree, scope["subjects"][0]["files_sha256"])
    return out


def results_hashes(run_dir):
    base = Path(run_dir) / "results"
    return {p.relative_to(run_dir).as_posix(): sha256_file(p) for p in sorted(base.rglob("*.json"))}


def has_survivors(results):
    return any(m["outcome"] == "survived"
               for rel, obj in results.items() if rel.startswith("results/") and isinstance(obj, dict)
               for m in obj.get("mutants", []))


def write_results(run_dir, results):
    for rel, obj in results.items():
        path = Path(run_dir) / rel
        if isinstance(obj, str):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(obj, encoding="utf-8")
        else:
            write_json(path, obj)


def run(run_dir, now, workdir=None):
    current = state.require(run_dir, "FROZEN")
    scope = load_scope(run_dir, require_pins=True)
    plan.require_agreement(run_dir, scope)  # also re-verifies the consent chain and head
    with tempfile.TemporaryDirectory(prefix="aac-run-", dir=workdir) as tmp:
        trees, licenses = pins.materialize(scope, tmp)
        fresh = plan.build_plan(run_dir, scope, trees, identity_for(scope))
        if plan.plan_hash(fresh) != current["plan_sha256"]:
            raise PlanError("run inputs no longer match the frozen plan hash")
        results = execute(run_dir, scope, trees)
        if plan.run_files(run_dir) != read_json(Path(run_dir) / plan.FILE)["core"]["run_files"]:
            raise PlanError("run-owned files changed during the run")
    write_results(run_dir, results)
    for i, text in licenses.items():
        if text is not None:
            (Path(run_dir) / f"UPSTREAM-LICENSE-{i}.txt").write_text(text, encoding="utf-8")
    state.transition(run_dir, "RUN", now, note="measured", results_sha256=results_hashes(run_dir))
    return results
