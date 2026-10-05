"""Lab settings from lab.toml: the current directory first, then this repository."""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(root: Path | None = None) -> dict:
    if root is None:
        root = Path.cwd() if (Path.cwd() / "lab.toml").is_file() else REPO_ROOT
    path = Path(root) / "lab.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return {"org": data.get("org"), "runs_dir": Path(root) / data.get("runs_dir", "runs")}
