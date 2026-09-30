"""Engine interface (RUN-PROTOCOL-v0.3 §6)."""

from dataclasses import dataclass, field
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Outcome:
    fault_id: str
    moved: int                      # cases whose projection changed without a crash
    crashed: int                    # cases that crashed, timed out or printed no projection
    engine_verdict: str | None = None  # engine-native verdict the lab does not map
    diff: dict = field(default_factory=dict)


class Engine:
    name = "abstract"

    def identity(self) -> dict:
        raise NotImplementedError

    def measure(self, tree, row, controls, faults) -> dict:
        """{"controls": {"positive": Outcome, "inert": Outcome},
        "faults": [Outcome, ...], "engine_report": dict | None}"""
        raise NotImplementedError


def get_engine(config):
    name = config["name"]
    if name == "native":
        from .native import NativeEngine
        return NativeEngine(timeout=config.get("timeout_seconds", 60))
    if name == "corpus_adequacy":
        from .corpus_adequacy import CorpusAdequacyEngine
        return CorpusAdequacyEngine(config)
    raise ValueError(f"unknown engine {name!r}")


def lab_code():
    """SHA-256 of every lab module, so the frozen plan covers the code that measures."""
    from ..canonical import sha256_file
    return {p.relative_to(LAB_ROOT).as_posix(): sha256_file(p)
            for p in sorted(LAB_ROOT.rglob("*.py")) if "__pycache__" not in p.parts}


def identity_for(scope):
    """Engine and lab code identity recorded in the frozen plan."""
    if scope["kind"] != "adequacy":
        return {"name": "verification", "lab_code": lab_code()}
    ident = {"primary": get_engine(scope["engine"]).identity(), "lab_code": lab_code()}
    cross = scope["engine"].get("cross_check")
    if cross:
        ident["cross_check"] = get_engine({**scope["engine"], "name": cross}).identity()
    return ident
