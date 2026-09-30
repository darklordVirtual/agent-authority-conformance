"""Native stdlib engine: one anchor replacement per tree copy, adapter per case.

Each case runs in its own subprocess with a minimal environment and a timeout.
A non-zero exit, a timeout, no output or a projection that is not a JSON object
with every declared field counts as a crash for that case.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ..canonical import sha256_file
from ..errors import EngineError
from ..faults import apply_mutation, read_source, write_source
from .base import Engine, Outcome

CRASH = "CRASH"
CASE_DIR = ".lab-cases"


class NativeEngine(Engine):
    name = "native"

    def __init__(self, timeout=60):
        self.timeout = timeout

    def identity(self):
        return {"name": self.name, "sha256": sha256_file(Path(__file__)), "timeout_seconds": self.timeout}

    def _command(self, row, case_file):
        parts = [sys.executable if part == "python3" else part for part in row["command"]]
        return [part.replace("{case}", str(case_file)) for part in parts]

    def run_case(self, tree, row, index, case_id):
        case_dir = Path(tree) / CASE_DIR
        case_dir.mkdir(exist_ok=True)
        # Named by index: case ids may contain path separators or spaces.
        case_file = case_dir / f"{index:05d}.json"
        case_file.write_text(json.dumps({"id": case_id}), encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"}
        if "SYSTEMROOT" in os.environ:
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        try:
            result = subprocess.run(self._command(row, case_file), cwd=tree, env=env,
                                    capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return CRASH
        if result.returncode != 0:
            return CRASH
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            return CRASH
        try:
            # Adapters may print warnings first; the projection is the last line.
            out = json.loads(lines[-1])
        except json.JSONDecodeError:
            return CRASH
        if not isinstance(out, dict) or any(key not in out for key in row["projection"]):
            return CRASH
        return {key: out[key] for key in row["projection"]}

    def baseline(self, tree, row):
        results = {cid: self.run_case(tree, row, i, cid) for i, cid in enumerate(row["cases"])}
        crashed = [cid for cid, value in results.items() if value == CRASH]
        if crashed:
            raise EngineError(f"row {row['id']}: the unmutated baseline crashed on {', '.join(crashed)}")
        return results

    def mutant(self, tree, row, mutation, baseline):
        with tempfile.TemporaryDirectory(prefix="aac-mutant-") as tmp:
            copy = Path(tmp) / "tree"
            shutil.copytree(tree, copy, ignore=shutil.ignore_patterns(CASE_DIR, "__pycache__"))
            target = copy / mutation["file"]
            write_source(target, apply_mutation(read_source(target), mutation))
            moved, crashed, diff = 0, 0, {}
            for i, cid in enumerate(row["cases"]):
                got = self.run_case(copy, row, i, cid)
                if got == CRASH:
                    crashed += 1
                    diff[cid] = {"baseline": baseline[cid], "mutant": CRASH}
                elif got != baseline[cid]:
                    moved += 1
                    diff[cid] = {"baseline": baseline[cid], "mutant": got}
        return Outcome(mutation["id"], moved, crashed, None, diff)

    def measure(self, tree, row, controls, faults):
        base = self.baseline(tree, row)
        return {
            "controls": {k: self.mutant(tree, row, controls[k], base) for k in ("positive", "inert")},
            "faults": [self.mutant(tree, row, fault, base) for fault in faults],
            "engine_report": None,
        }
