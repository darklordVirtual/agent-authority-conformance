"""Repository-level lab settings from lab.toml."""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(root: Path = REPO_ROOT) -> dict:
    path = Path(root) / "lab.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return {"org": data.get("org"), "runs_dir": Path(root) / data.get("runs_dir", "runs")}
