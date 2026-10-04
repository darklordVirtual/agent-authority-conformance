"""Verification kind: the runner's own per-claim checks over pinned inputs.

The producer's expected outcomes are never passed to a check. They are read
only after every record exists, and agreement is reported separately; it is
not a result and not independent evidence.
"""

import copy
import importlib.util
from pathlib import Path

from ..canonical import read_json, sha256_file, sha256_json
from ..errors import EngineError, LabError, ScopeError

RESULTS = ("ESTABLISHED", "CONTRADICTED", "NOT_ESTABLISHED")
EXPECTED_FILE = "producer-expected.json"


def load_check(run_dir, spec):
    module_name, _, function = spec.partition(":")
    path = Path(run_dir) / "verifier" / f"{module_name}.py"
    if not function or not path.is_file():
        raise ScopeError(f"check {spec!r} must name <module>:<function> in verifier/")
    module_spec = importlib.util.spec_from_file_location(f"aac_verifier_{module_name}", path)
    module = importlib.util.module_from_spec(module_spec)
    try:
        module_spec.loader.exec_module(module)
    except Exception as exc:  # the run stops; a verifier that cannot load produces no results
        raise EngineError(f"verifier module {path.name} failed to load: {type(exc).__name__}: {exc}") from exc
    check = getattr(module, function, None)
    if not callable(check):
        raise ScopeError(f"check {spec!r}: {function} is not a function in {path.name}")
    return check


def _error(record, code, message):
    record.update({"execution": "ERROR", "result": None,
                   "verifier_error": {"code": code, "message": message}})
    return record


def run_claim(check, claim, input_id, document, context, digest):
    record = {"input": input_id, "claim": claim["id"], "evidence": [f"sha256:{digest}"]}
    try:
        out = check(document, context)
    except Exception as exc:  # a verifier crash is a non-verdict, never a finding
        return _error(record, "exception", f"{type(exc).__name__}: {exc}")
    if not isinstance(out, dict):
        return _error(record, "bad_return", "check must return a dict")
    execution = out.get("execution", "COMPLETED")
    if execution in ("INVALID_INPUT", "UNSUPPORTED"):
        record.update({"execution": execution, "result": None,
                       "verifier_error": {"code": execution.lower(), "message": str(out.get("message", ""))}})
        return record
    if execution != "COMPLETED":
        return _error(record, "bad_execution", f"execution {execution!r} is not allowed from a check")
    result, reads = out.get("result"), out.get("reads")
    obligations = out.get("unresolved_obligations", [])
    if result not in RESULTS:
        return _error(record, "bad_result", f"result {result!r} is not one of {', '.join(RESULTS)}")
    if not (isinstance(reads, list) and set(reads) <= set(claim["reads_fields"])):
        return _error(record, "undeclared_read",
                      f"reads {reads!r} must be a subset of the declared {claim['reads_fields']!r}")
    if not (isinstance(obligations, list) and all(isinstance(o, str) and o for o in obligations)):
        return _error(record, "bad_obligations", "unresolved_obligations must be a list of strings")
    if result == "NOT_ESTABLISHED" and not obligations:
        return _error(record, "missing_obligations", "NOT_ESTABLISHED needs unresolved_obligations")
    if result != "NOT_ESTABLISHED" and obligations:
        return _error(record, "unexpected_obligations", f"{result} must carry no unresolved_obligations")
    record.update({"execution": "COMPLETED", "result": result, "reads": reads,
                   "unresolved_obligations": obligations})
    return record


def load_input(path):
    """A file is one JSON document. A directory is a bundle {relative path: document}
    of its .json files; its digest is the hash of the canonical {path: sha256} map."""
    path = Path(path)
    if path.is_dir():
        files = sorted(p for p in path.rglob("*.json") if p.is_file())
        bundle = {p.relative_to(path).as_posix(): read_json(p) for p in files}
        digest = sha256_json({p.relative_to(path).as_posix(): sha256_file(p) for p in files})
        return bundle, digest
    return read_json(path), sha256_file(path)


def execute(run_dir, scope, trees, admission=None):
    """admission: {"inputs": {id: {"decision", "rationale", ...}}} or None (all admitted).
    A claim over an input that is not ADMITTED is a non-verdict and its check never runs."""
    refused = {} if admission is None else {
        i: a for i, a in admission["inputs"].items() if a["decision"] != "ADMITTED"}
    inputs = {}
    for item in scope["inputs"]:
        try:
            inputs[item["id"]] = load_input(Path(trees[item["subject"]]) / item["path"])
        except (LabError, OSError) as exc:
            inputs[item["id"]] = exc  # malformed input is a non-verdict for every claim on it
    context = {"reference_time": scope.get("reference_time")}
    records = []
    for claim in scope["claims"]:
        check = load_check(run_dir, claim["check"])
        for input_id in claim["inputs"]:
            if input_id in refused:
                records.append({"input": input_id, "claim": claim["id"], "evidence": [],
                                "execution": "NOT_ADMITTED", "result": None,
                                "verifier_error": {"code": "not_admitted",
                                                   "message": f"{refused[input_id]['decision']}: "
                                                              f"{refused[input_id]['rationale']}"}})
                continue
            if isinstance(inputs[input_id], Exception):
                records.append({"input": input_id, "claim": claim["id"], "evidence": [],
                                "execution": "INVALID_INPUT", "result": None,
                                "verifier_error": {"code": "invalid_input", "message": str(inputs[input_id])}})
                continue
            document, digest = inputs[input_id]
            records.append(run_claim(check, claim, input_id, copy.deepcopy(document), dict(context), digest))
    return records


def agreement(run_dir, records):
    path = Path(run_dir) / EXPECTED_FILE
    if not path.is_file():
        return None
    expected = read_json(path)
    rows = []
    for record in records:
        want = expected.get(record["input"], {}).get(record["claim"])
        if want is not None:
            rows.append({"input": record["input"], "claim": record["claim"], "ours": record["result"],
                         "producer": want, "agree": want == record["result"]})
    return {"note": "Agreement with the producer's published expectations. This is not a result "
                    "and not independent evidence.", "rows": rows}
