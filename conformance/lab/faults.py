"""Fault and control definitions and the one text operation that applies them."""

from pathlib import Path

from .canonical import read_json
from .errors import PlanError, ScopeError

SETS = ("known", "held_out")
FAULT_KEYS = ("id", "class", "file", "anchor", "replacement")


def _fault_problems(fault, where):
    if not isinstance(fault, dict):
        return [f"{where} must be an object"]
    p = [f"{where}.{k} must be a nonempty string" for k in FAULT_KEYS
         if not (isinstance(fault.get(k), str) and fault[k])]
    if not p and fault["anchor"] == fault["replacement"]:
        p.append(f"{where}: anchor equals replacement")
    return p


def load_fault_set(path):
    doc = read_json(path)
    p = []
    if not (isinstance(doc.get("name"), str) and doc["name"]):
        p.append(f"{path}: name is required")
    if doc.get("set") not in SETS:
        p.append(f"{path}: set must be one of {', '.join(SETS)}")
    source = doc.get("source")
    if not (isinstance(source, dict) and source.get("author")
            and isinstance(source.get("ref"), str) and source["ref"].startswith("https://")):
        p.append(f"{path}: source needs author and an https ref")
    faults = doc.get("faults")
    if not (isinstance(faults, list) and faults):
        p.append(f"{path}: faults must be a nonempty list")
    else:
        for i, fault in enumerate(faults):
            p.extend(_fault_problems(fault, f"{path}: faults[{i}]"))
        ids = [f.get("id") for f in faults if isinstance(f, dict)]
        if len(ids) != len(set(ids)):
            p.append(f"{path}: fault ids must be unique")
    if p:
        raise ScopeError("; ".join(p))
    return doc


def load_control(path, polarity):
    doc = read_json(path)
    p = _fault_problems(doc, str(path))
    if doc.get("polarity") != polarity:
        p.append(f"{path}: polarity must be {polarity!r}")
    if p:
        raise ScopeError("; ".join(p))
    return doc


def row_mutations(run_dir, scope, row):
    """(controls, faults) for one row. Each fault carries its set and set name."""
    run_dir = Path(run_dir)
    controls = {k: load_control(run_dir / scope["controls"][k], k) for k in ("positive", "inert")}
    faults, seen = [], {controls["positive"]["id"], controls["inert"]["id"]}
    for rel in row["fault_sets"]:
        doc = load_fault_set(run_dir / rel)
        for fault in doc["faults"]:
            if fault["id"] in seen:
                raise ScopeError(f"fault id {fault['id']} is used twice in row {row['id']}")
            seen.add(fault["id"])
            faults.append({**fault, "set": doc["set"], "set_name": doc["name"]})
    return controls, faults


def read_source(path):
    """Read text without newline translation, so anchors match the pinned bytes."""
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def write_source(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def apply_mutation(text, mutation):
    count = text.count(mutation["anchor"])
    if count != 1:
        raise PlanError(f"{mutation['id']}: anchor occurs {count} times in {mutation['file']}; "
                        "it must occur exactly once")
    return text.replace(mutation["anchor"], mutation["replacement"], 1)
