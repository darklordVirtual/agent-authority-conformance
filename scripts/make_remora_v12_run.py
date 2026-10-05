#!/usr/bin/env python3
"""Create the SELF_RUN reference run runs/remora-es-v12-adequacy/.

The run measures REMORA-research evidence-sufficiency v1.2 at c1345b1 with the
fault definitions Rul1an published in corpus-adequacy/remora-es-v11-adequacy at
9f38519 (known rows and the six disclosed additional operators), converted to
lab fault sets with attribution. This script only writes the run directory and
pins it; freezing and running need consent events recorded by the maintainer.

The fault anchors quote BUSL-1.1 REMORA code, so the run directory stays under
the gitignored runs/ and is delivered only through a private repository.

    python scripts/make_remora_v12_run.py [--runs-dir runs]
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conformance.lab import lifecycle, pins  # noqa: E402
from conformance.lab.canonical import utc_now, write_json  # noqa: E402
from conformance.lab.config import load_config  # noqa: E402

REMORA = "https://github.com/darklordVirtual/REMORA-research"
REMORA_COMMIT = "c1345b1f9e0f877454bf996b2160d533c5a9b16a"
ADEQUACY = "https://github.com/corpus-adequacy/remora-es-v11-adequacy"
ADEQUACY_COMMIT = "9f3851995bbe395e510dde9ce9a03ebb6f1f965a"
CHECKER = "conformance/evidence-sufficiency-v1/checker.py"
SUITE = "conformance/evidence-sufficiency-v1.2"
RUN_ID = "remora-es-v12-adequacy"

ADAPTER = '''"""AAC adapter for REMORA evidence-sufficiency v1.2. Upstream files are unchanged.

usage: remora_case.py verdict|guidance|runner <case file>
"""
import json
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE / "conformance" / "evidence-sufficiency-v1.2"
sys.path.insert(0, str(SUITE))
from run_evidence_sufficiency import assess, build_record, load_json  # noqa: E402

mode, case_file = sys.argv[1], sys.argv[2]
if mode == "runner":
    # Only the failures list is scored, never the recorded source hashes.
    print(json.dumps({"failures": "|".join(sorted(build_record()["failures"]))}))
    raise SystemExit(0)
case_id = json.loads(Path(case_file).read_text(encoding="utf-8"))["id"]
case = {c["id"]: c for c in load_json(SUITE / "cases.json")["cases"]}[case_id]
scope = {"kind": "synthetic_fixture", "suite": "evidence-sufficiency-v1.2", "bounded": True, "case": case_id}
verdict = assess(case["claim"], deepcopy(case["observations"]), scope=scope).as_dict()
if mode == "verdict":
    print(json.dumps({"status": verdict["status"], "reason": verdict["reason"]}))
else:
    print(json.dumps({"missing_evidence": "|".join(verdict["missing_evidence"]),
                      "decisive_if": verdict.get("decisive_if") or ""}))
'''


def fault_class(label):
    match = re.match(r"\[(\w+)\]", label)
    if not match:
        return "other"
    return "additional-disclosed" if match.group(1) == "H" else f"class-{match.group(1)}"


def convert(mutants, prefix, source_path):
    faults = [m for m in mutants if not m.get("control")]
    return [{"id": f"{prefix}{i:03d}", "label": m["label"], "class": fault_class(m["label"]), "file": CHECKER,
             "anchor": m["anchor"], "replacement": m["replacement"],
             **({"rationale": m["rationale"]} if m.get("rationale") else {})}
            for i, m in enumerate(faults, 1)], source_path


def fault_set(name, faults, source_path, note):
    return {"name": name, "set": "known", "note": note,
            "source": {"author": "Rul1an", "ref": f"{ADEQUACY}/blob/{ADEQUACY_COMMIT}/{source_path}"},
            "faults": faults}


def build(runs_dir):
    now = utc_now()
    with tempfile.TemporaryDirectory(prefix="aac-remora-") as tmp:
        ref = pins.fetch(ADEQUACY, ADEQUACY_COMMIT, Path(tmp) / "adequacy")
        remora = pins.fetch(REMORA, REMORA_COMMIT, Path(tmp) / "remora")
        manifest = lambda row: json.loads((ref / "manifests" / f"ca_{row}.manifest.json").read_text(encoding="utf-8"))
        row1, row2, row3 = (manifest(r) for r in ("known-row1-verdict", "known-row2-guidance", "known-row3-runner"))
        additional = json.loads((ref / "additional-faults-FROZEN.json").read_text(encoding="utf-8"))
        controls = [m for m in row1["mutants"]["remora"] if m.get("control")]
        assert [m for m in row2["mutants"]["remora"] if not m.get("control")] == \
               [m for m in row3["mutants"]["remora"] if not m.get("control")], "row2/row3 known faults differ"
        case_ids = [c["id"] for c in json.loads((remora / SUITE / "cases.json").read_text(encoding="utf-8"))["cases"]]

    run_dir = lifecycle.init(runs_dir, RUN_ID, "adequacy", now)
    known_v, src_v = convert(row1["mutants"]["remora"], "KV", "manifests/ca_known-row1-verdict.manifest.json")
    known_g, src_g = convert(row2["mutants"]["remora"], "KG", "manifests/ca_known-row2-guidance.manifest.json")
    added, src_a = convert(additional["mutants"], "AD", "additional-faults-FROZEN.json")
    write_json(run_dir / "faults" / "known-verdict.json",
               fault_set("rul1an-v11-known-verdict", known_v, src_v, "Row 1 selection as run on v1.0 and v1.1."))
    write_json(run_dir / "faults" / "known-guidance-runner.json",
               fault_set("rul1an-v11-known-103", known_g, src_g, "Rows 2 and 3 selection as run on v1.0 and v1.1."))
    write_json(run_dir / "faults" / "additional-disclosed.json",
               fault_set("rul1an-v11-additional-disclosed", added, src_a,
                         "Precommitted by hash before the v1.1 run and disclosed since; now a known set. "
                         "v1.2 cases were written with these faults in view."))
    for control in controls:
        polarity = control["control_polarity"]
        write_json(run_dir / "controls" / f"{polarity}.json",
                   {"id": f"CONTROL-{polarity}", "class": "control", "polarity": polarity, "label": control["label"],
                    "file": CHECKER, "anchor": control["anchor"], "replacement": control["replacement"]})
    (run_dir / "adapter").mkdir()
    (run_dir / "adapter" / "remora_case.py").write_text(ADAPTER, encoding="utf-8")

    def row(row_id, mode, projection, cases, sets, expected=False):
        entry = {"id": row_id, "command": ["python3", "-B", "remora_case.py", mode, "{case}"],
                 "projection": projection, "cases": cases, "fault_sets": sets}
        if expected:
            entry["expected_from"] = {"path": f"{SUITE}/cases.json", "list_key": "cases", "id_key": "id",
                                      "field": "expected"}
        return entry

    scope = lifecycle.skeleton(RUN_ID, "adequacy")
    scope.update({
        "agreement_ref": "https://github.com/darklordVirtual/REMORA-research/issues/629",
        "independence": "SELF_RUN",
        "runner": {"project": "Agent Authority Conformance", "maintainers": ["darklordVirtual"]},
        "agreement_parties": ["darklordVirtual"],
        "subjects": [{"project": "REMORA-research", "maintainers": ["darklordVirtual"], "repo": REMORA,
                      "commit": REMORA_COMMIT,
                      "paths": ["conformance/evidence-sufficiency-v1", SUITE], "files_sha256": {},
                      "license": "BUSL-1.1", "attribution": "darklordVirtual/REMORA-research"}],
        "rows": [
            row("row1-verdict", "verdict", ["status", "reason"], case_ids,
                ["faults/known-verdict.json", "faults/additional-disclosed.json"], expected=True),
            row("row2-guidance", "guidance", ["missing_evidence", "decisive_if"], case_ids,
                ["faults/known-guidance-runner.json", "faults/additional-disclosed.json"]),
            row("row3-runner", "runner", ["failures"], ["runner"],
                ["faults/known-guidance-runner.json", "faults/additional-disclosed.json"]),
        ],
        "engine": {"name": "native", "cross_check": None},
        "claim_ceiling": {
            "establishes": ["which of Rul1an's published v1.1 fault definitions the v1.2 cases and runner "
                            "distinguish from the pinned checker, per declared projection"],
            "does_not_establish": [
                "independent evidence (the runner maintains the subject)",
                "generalisation: v1.2 cases were written after these faults were known",
                "that the checker or its inference rules are correct",
                "anything about production use"],
        },
        "publication": {"private_first": True, "approvers": ["darklordVirtual", "Rul1an"],
                        "unreleased_citable": False},
    })
    write_json(run_dir / "SCOPE.json", scope)
    lifecycle.pin(run_dir)
    return run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", type=Path, default=load_config()["runs_dir"])
    args = parser.parse_args()
    run_dir = build(args.runs_dir)
    print(f"created and pinned {run_dir}")
    print("Next: record scope_agreed and run_authorized (darklordVirtual), then freeze, publish the hash, "
          "freeze --published-ref, run, package. Ask Rul1an before sharing: the fault definitions are theirs.")


if __name__ == "__main__":
    main()
