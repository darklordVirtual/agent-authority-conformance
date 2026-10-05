"""Adequacy rows: classification, controls and row status (RUN-PROTOCOL-v0.3 §5.4).

A survivor means the corpus did not distinguish that fault on the declared
projection. It is never reported as a checker defect.
"""

import shutil
from pathlib import Path

from ..canonical import read_json
from ..engines.native import NativeEngine
from ..errors import EngineError, PlanError
from ..faults import row_mutations

OUTCOMES = ("killed", "killed_crash", "survived", "not_measured")
SURVIVOR_NOTE = "not distinguished on the declared projection by this corpus; not a checker defect"


def classify(outcome):
    if outcome.engine_verdict is not None:
        return "not_measured"
    if outcome.moved:
        return "killed"
    if outcome.crashed:
        return "killed_crash"
    return "survived"


def row_status(controls):
    # A crash is not a measured projection change, so it cannot satisfy the positive control.
    if classify(controls["positive"]) != "killed":
        return "VOID_NO_SCORE"
    inert = controls["inert"]
    if inert.moved or inert.crashed or inert.engine_verdict is not None:
        return "VOID"
    return "MEASURED"


def prepare_tree(run_dir, tree):
    """Copy run-owned adapter files into the tree root, as corpus-adequacy does."""
    adapter = Path(run_dir) / "adapter"
    if not adapter.is_dir():
        return
    for path in adapter.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            dest = Path(tree) / path.relative_to(adapter)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


def check_expected(tree, row, baseline):
    """Stop if the unmutated subject disagrees with its own published expectations."""
    spec = row.get("expected_from")
    if not spec:
        return
    doc = read_json(Path(tree) / spec["path"])
    expected = {case[spec["id_key"]]: case.get(spec["field"], {}) for case in doc[spec["list_key"]]}
    bad = [cid for cid in row["cases"]
           if {k: expected.get(cid, {}).get(k) for k in row["projection"]} != baseline[cid]]
    if bad:
        raise PlanError(f"row {row['id']}: baseline differs from the subject's own expected "
                        f"outcomes for {', '.join(bad)}")


def _counts(mutants, set_name):
    selected = [m for m in mutants if m["set_name"] == set_name]
    return {k: sum(m["outcome"] == k for m in selected) for k in OUTCOMES}


def execute_row(run_dir, scope, tree, row, engine):
    """Measure one row. Returns (row result, engine-native report or None)."""
    baseline = NativeEngine(timeout=scope.get("engine", {}).get("timeout_seconds", 60)).baseline(tree, row)
    check_expected(tree, row, baseline)
    controls, faults = row_mutations(run_dir, scope, row)
    measured = engine.measure(tree, row, controls, faults)
    by_id = {f["id"]: f for f in faults}
    reported = [o.fault_id for o in measured["faults"]]
    if sorted(reported) != sorted(by_id):
        raise EngineError(f"row {row['id']}: engine did not report exactly the declared faults")
    mutants = []
    for outcome in measured["faults"]:
        fault = by_id[outcome.fault_id]
        entry = {"fault_id": outcome.fault_id, "set": fault["set"], "set_name": fault["set_name"],
                 "class": fault["class"], "outcome": classify(outcome),
                 "moved": outcome.moved, "crashed": outcome.crashed, "diff": outcome.diff}
        if outcome.engine_verdict is not None:
            entry["engine_verdict"] = outcome.engine_verdict
        if entry["outcome"] == "survived":
            entry["note"] = SURVIVOR_NOTE
        mutants.append(entry)
    names = list(dict.fromkeys(f["set_name"] for f in faults))
    result = {
        "row": row["id"],
        "status": row_status(measured["controls"]),
        "engine": engine.identity(),
        "projection": row["projection"],
        "controls": {k: {"fault_id": o.fault_id, "outcome": classify(o), "moved": o.moved, "crashed": o.crashed}
                     for k, o in measured["controls"].items()},
        "counts_by_set": {name: _counts(mutants, name) for name in names},
        "mutants": mutants,
    }
    return result, measured.get("engine_report")
