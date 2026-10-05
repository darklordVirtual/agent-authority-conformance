"""Toy adapter: print the projection for one case as the last stdout line."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checker import decide  # noqa: E402

case_id = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["id"]
cases = {c["id"]: c for c in json.loads(Path("cases.json").read_text(encoding="utf-8"))["cases"]}
print(json.dumps(decide(cases[case_id]["input"])))
