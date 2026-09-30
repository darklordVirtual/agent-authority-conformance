"""Adapter to a pinned corpus-adequacy checkout (Rul1an/corpus-adequacy, MIT).

Translation only: the lab generates corpus-adequacy's manifest from its own
fault and control files, runs the pinned tool, and maps each reported verdict
to movement. Classification happens in kinds.adequacy like for any engine.
The tool's own report is kept beside the lab result; only its local manifest
path is replaced, and that transformation is recorded with both digests.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from ..canonical import sha256_bytes, sha256_file, sha256_json, write_json
from ..errors import EngineError
from .base import Engine, Outcome

DEFAULT_COMMIT = "5fa2ff587497b00ac684a767335b9068f7e520a6"
CRASH_HOWS = ("unexpected-exit", "timeout", "signal", "output-cap")
MAPPED = frozenset({"killed", "survived", "control-killed", "control-unchanged"})
CASE_DIR = ".lab-cases"


class CorpusAdequacyEngine(Engine):
    name = "corpus_adequacy"

    def __init__(self, config):
        self.commit = config.get("corpus_adequacy_commit", DEFAULT_COMMIT)
        self.tool_sha256 = config.get("corpus_adequacy_sha256")
        self.path = Path(os.environ.get("AAC_CORPUS_ADEQUACY") or config.get("corpus_adequacy_path") or ".")

    def _tool(self):
        tool = self.path / "corpus_adequacy.py"
        if not tool.is_file():
            raise EngineError("corpus-adequacy checkout not found; set AAC_CORPUS_ADEQUACY to its path")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.path, capture_output=True, text=True)
        if head.stdout.strip() != self.commit:
            raise EngineError(f"corpus-adequacy is at {head.stdout.strip() or 'unknown'}, pinned {self.commit}")
        if self.tool_sha256 and sha256_file(tool) != self.tool_sha256:
            raise EngineError("corpus_adequacy.py bytes differ from the pinned sha256")
        return tool

    def identity(self):
        return {"name": self.name, "commit": self.commit, "sha256": sha256_file(self._tool())}

    def manifest(self, row, controls, faults):
        files = {m["file"] for m in (controls["positive"], controls["inert"], *faults)}
        if len(files) != 1:
            raise EngineError(f"row {row['id']}: corpus-adequacy mutates one implementation file; "
                              f"these faults target {', '.join(sorted(files))}")
        implementation = files.pop()
        mutants = [{"label": controls[k]["id"], "control": True, "control_polarity": k,
                    "anchor": controls[k]["anchor"], "replacement": controls[k]["replacement"]}
                   for k in ("positive", "inert")]
        mutants += [{"label": f["id"], "anchor": f["anchor"], "replacement": f["replacement"]} for f in faults]
        return {
            "schema": "corpus-adequacy.manifest.v0", "runner": "process", "repo_root": ".",
            "implementation": implementation, "implementation_sources": [implementation], "build": [],
            "id_key": "vector_id", "vector_path_key": "path", "default_group": "aac", "equivalent": {},
            "entrypoint_command": [part.replace("{case}", "{vector}") for part in row["command"]],
            "outcome_from": row["projection"], "vectors": "aac_vectors.json", "mutants": {"aac": mutants},
        }

    @staticmethod
    def translate(label, row):
        if row is None:
            raise EngineError(f"corpus-adequacy report has no row for {label}")
        verdict, how = row["verdict"], row.get("how", "")
        if verdict not in MAPPED:
            return Outcome(label, 0, 0, verdict, {})
        if verdict in ("killed", "control-killed"):
            if how.startswith(CRASH_HOWS):
                return Outcome(label, 0, 1, None, {})
            return Outcome(label, max(int(row.get("moved") or 0), 1), 0, None, {})
        return Outcome(label, 0, 0, None, {})

    def measure(self, tree, row, controls, faults):
        tool, tree = self._tool(), Path(tree)
        (tree / CASE_DIR).mkdir(exist_ok=True)
        vectors = []
        for i, case_id in enumerate(row["cases"]):
            (tree / CASE_DIR / f"{i:05d}.json").write_text(json.dumps({"id": case_id}), encoding="utf-8")
            vectors.append({"vector_id": case_id, "path": f"{CASE_DIR}/{i:05d}.json"})
        write_json(tree / "aac_vectors.json", {"vectors": vectors})
        manifest_path = tree / f"aac_{row['id']}.manifest.json"
        write_json(manifest_path, self.manifest(row, controls, faults))
        result = subprocess.run([sys.executable, "-B", str(tool), str(manifest_path), "--json"],
                                cwd=tree, capture_output=True, text=True)
        if result.returncode not in (0, 1):
            raise EngineError(f"corpus-adequacy exited {result.returncode}: {result.stderr.strip()[:500]}")
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise EngineError(f"corpus-adequacy printed no JSON report: {exc}") from exc
        by_label = {m["label"]: m for m in report.get("mutants", [])}
        delivery = {**report, "manifest": manifest_path.name}
        return {
            "controls": {k: self.translate(controls[k]["id"], by_label.get(controls[k]["id"]))
                         for k in ("positive", "inert")},
            "faults": [self.translate(f["id"], by_label.get(f["id"])) for f in faults],
            "engine_report": {
                "report": delivery,
                "original_to_delivery": {
                    "original_sha256": sha256_bytes(result.stdout.encode("utf-8")),
                    "delivery_sha256": sha256_json(delivery),
                    "transformation": "only the top-level local manifest path is replaced by the manifest "
                                      "file name; the original is retained outside the package",
                },
                "original_text": result.stdout,
            },
        }
