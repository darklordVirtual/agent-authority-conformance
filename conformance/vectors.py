"""Frozen reference vectors: verify their bytes, check an implementation against them.

    python -m conformance.vectors verify                 # digests only (standard library)
    python -m conformance.vectors check                  # this repository's reference rules
    python -m conformance.vectors run --impl "CMD ..."   # any implementation, over stdio
    python -m conformance.vectors serve                  # the reference, as an implementation

The protocol, the operations and what agreement does and does not establish are
in docs/REFERENCE-VECTORS.md. ``run`` executes the command it is given and
nothing else; it never fetches or installs anything. Running a third party's
command is the operator's decision, not this tool's.

Agreement is reported per vector and per operation. There is no score: a count
of agreeing vectors is not a conformance level, and the report holds no
aggregate key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SUITE = "aacp-reference-vectors-v1"
SUITE_DIR = ROOT / "vectors" / SUITE

AGREES, DISAGREES, NOT_IMPLEMENTED, ERROR = "AGREES", "DISAGREES", "NOT_IMPLEMENTED", "ERROR"


class VectorError(ValueError):
    """The suite's bytes are not the frozen ones, or a vector file is malformed."""


# ── the bytes ────────────────────────────────────────────────────────────────


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_suite(suite_dir: Path = SUITE_DIR) -> list[str]:
    """Problems with the suite's bytes; empty when every digest matches."""
    problems: list[str] = []
    manifest_path = suite_dir / "MANIFEST.json"
    sums_path = suite_dir / "SHA256SUMS"
    if not manifest_path.is_file() or not sums_path.is_file():
        return [f"{suite_dir}: MANIFEST.json or SHA256SUMS is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"MANIFEST.json is not JSON: {exc}"]
    if manifest.get("suite") != suite_dir.name:
        problems.append(f"MANIFEST.json names suite {manifest.get('suite')!r}, "
                        f"the directory is {suite_dir.name!r}")
    sums: dict[str, str] = {}
    for line in sums_path.read_text(encoding="ascii").splitlines():
        digest, _, name = line.partition("  ")
        sums[name] = digest
    listed = {entry["path"]: entry["sha256"] for entry in manifest.get("files", [])}
    for name, digest in listed.items():
        path = suite_dir / name
        if not path.is_file():
            problems.append(f"{name}: listed in MANIFEST.json, absent")
            continue
        actual = _sha256(path.read_bytes())
        if actual != digest:
            problems.append(f"{name}: sha256 {actual}, MANIFEST.json says {digest}")
        if sums.get(name) != digest:
            problems.append(f"{name}: SHA256SUMS and MANIFEST.json disagree")
    if sums.get("MANIFEST.json") != _sha256(manifest_path.read_bytes()):
        problems.append("MANIFEST.json: its digest in SHA256SUMS does not match")
    extra = set(sums) - set(listed) - {"MANIFEST.json"}
    for name in sorted(extra):
        problems.append(f"{name}: in SHA256SUMS, not in MANIFEST.json")
    present = {p.name for p in suite_dir.iterdir() if p.is_file()}
    for name in sorted(present - set(listed) - {"MANIFEST.json", "SHA256SUMS", "README.md"}):
        problems.append(f"{name}: present but not listed")
    return problems


def load_operations(suite_dir: Path = SUITE_DIR) -> list[dict[str, Any]]:
    problems = verify_suite(suite_dir)
    if problems:
        raise VectorError("; ".join(problems))
    manifest = json.loads((suite_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    out = []
    for entry in manifest["files"]:
        doc = json.loads((suite_dir / entry["path"]).read_text(encoding="utf-8"))
        if doc.get("operation") != entry["operation"]:
            raise VectorError(f"{entry['path']}: operation does not match MANIFEST.json")
        if [v["id"] for v in doc["vectors"]] != entry["vector_ids"]:
            raise VectorError(f"{entry['path']}: vector ids do not match MANIFEST.json")
        out.append(doc)
    return out


# ── the reference, as one function per operation ─────────────────────────────


def _reference() -> dict[str, Callable[[Any], dict[str, Any]]]:
    from jsonschema import ValidationError

    from . import agentavow_tool_binding as avow
    from .boundary import InvalidInput, UnsupportedVerification, evaluate
    from .coverage import CoverageError, component_matrix
    from .lab import canonical
    from .lab.errors import ScopeError
    from .observed_effect_vantage import evaluate_observation_vantage

    def e_rule(inp):
        try:
            return {"result": evaluate(inp)}
        except InvalidInput:
            return {"result": {"verification_status": "INVALID_INPUT", "status": None}}
        except UnsupportedVerification:
            return {"result": {"verification_status": "UNSUPPORTED", "status": None}}

    def oe08(inp):
        verdict = evaluate_observation_vantage(
            inp["record"], trusted_control_domains=inp["trusted_control_domains"])
        return {"result": verdict.as_dict()}

    def canonical_json(inp):
        data = canonical.dumps(json.loads(inp["text"]))
        return {"result": {"canonical_utf8": data.decode("utf-8"),
                           "sha256": canonical.sha256_bytes(data)}}

    def read_json(inp):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.json"
            path.write_text(inp["text"], encoding="utf-8")
            try:
                return {"result": canonical.read_json(path)}
            except ScopeError as exc:
                code = "DUPLICATE_KEY" if "duplicate JSON key" in str(exc) else "INVALID_JSON"
                return {"error": code}

    def coverage(inp):
        try:
            return {"result": component_matrix(inp["assessment"])}
        except CoverageError:
            return {"error": "COVERAGE_ERROR"}
        except ValidationError:
            return {"error": "INVALID_ASSESSMENT"}

    return {
        "e_rule.evaluate": e_rule,
        "oe08.observation_vantage": oe08,
        "agentavow.tool_key": lambda inp: {"result": avow.tool_key(inp["name"])},
        "agentavow.tool_digest": lambda inp: {"result": avow.tool_digest(inp["tool"])},
        "agentavow.binding": lambda inp: {"result": avow.evaluate(inp["vector"], inp["fixture"])},
        "lab.canonical_json": canonical_json,
        "lab.read_json": read_json,
        "lab.forbidden_keys": lambda inp: {"result": canonical.find_forbidden_keys(inp["value"])},
        "coverage.component_matrix": coverage,
    }


def answer(request: Any, reference=None) -> dict[str, Any]:
    """One protocol response from the reference: {result} or {error}."""
    reference = reference or _reference()
    if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
        return {"error": "INVALID_REQUEST"}
    handler = reference.get(request["operation"])
    if handler is None:
        return {"error": "UNSUPPORTED_OPERATION"}
    return handler(request.get("input"))


# ── comparing ────────────────────────────────────────────────────────────────


def _same(expected: dict[str, Any], actual: Any, compare: list[str] | None) -> bool:
    if not isinstance(actual, dict):
        return False
    if "error" in expected:
        return set(actual) == {"error"} and actual["error"] == expected["error"]
    if set(actual) != {"result"}:
        return False
    want, got = expected["result"], actual["result"]
    if compare is None:
        return _strict_equal(want, got)
    if not isinstance(got, dict):
        return False
    return all(k in got and _strict_equal(want.get(k), got[k]) for k in compare)


def _strict_equal(a: Any, b: Any) -> bool:
    """JSON equality that keeps true apart from 1 and 1.0 apart from 1."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def judge(doc: dict[str, Any], respond: Callable[[dict[str, Any]], Any]) -> list[dict[str, Any]]:
    rows = []
    for v in doc["vectors"]:
        request = {"operation": doc["operation"], "vector_id": v["id"], "input": v["input"]}
        try:
            actual = respond(request)
        except _ImplementationFailed as exc:
            rows.append({"id": v["id"], "outcome": ERROR, "detail": str(exc)})
            continue
        if actual == {"error": "UNSUPPORTED_OPERATION"} and v["expected"] != actual:
            rows.append({"id": v["id"], "outcome": NOT_IMPLEMENTED})
        elif _same(v["expected"], actual, v.get("compare")):
            rows.append({"id": v["id"], "outcome": AGREES})
        else:
            rows.append({"id": v["id"], "outcome": DISAGREES,
                         "expected": v["expected"], "actual": actual})
    return rows


class _ImplementationFailed(Exception):
    pass


def _subprocess_responder(argv: list[str], timeout: float):
    def respond(request):
        try:
            done = subprocess.run(argv, input=json.dumps(request, ensure_ascii=False) + "\n",
                                  capture_output=True, text=True, encoding="utf-8",
                                  timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise _ImplementationFailed(f"no answer within {timeout} s") from exc
        except OSError as exc:
            raise _ImplementationFailed(f"cannot start the implementation: {exc}") from exc
        if done.returncode != 0:
            raise _ImplementationFailed(
                f"exit status {done.returncode}: {done.stderr.strip()[-300:]}")
        # Lines end in "\n" only: str.splitlines() would also split a valid JSON
        # answer at a literal U+2028 (found by canon-line-separator-literal).
        lines = [line for line in done.stdout.split("\n") if line.strip()]
        if len(lines) != 1:
            raise _ImplementationFailed(f"expected one JSON line, got {len(lines)}")
        try:
            return json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise _ImplementationFailed(f"the answer is not JSON: {exc}") from exc
    return respond


def report(operations: list[dict[str, Any]], respond, only: set[str] | None) -> dict[str, Any]:
    out: dict[str, Any] = {"suite": SUITE, "operations": []}
    for doc in operations:
        if only is not None and doc["operation"] not in only:
            continue
        rows = judge(doc, respond)
        by_outcome: dict[str, list[str]] = {k: [] for k in (AGREES, DISAGREES,
                                                            NOT_IMPLEMENTED, ERROR)}
        for row in rows:
            by_outcome[row["outcome"]].append(row["id"])
        out["operations"].append({"operation": doc["operation"], "vectors": rows,
                                  "by_outcome": by_outcome})
    return out


def _failed(rep: dict[str, Any]) -> bool:
    return any(op["by_outcome"][DISAGREES] or op["by_outcome"][ERROR]
               for op in rep["operations"])


def _print_summary(rep: dict[str, Any]) -> None:
    for op in rep["operations"]:
        parts = ", ".join(f"{k.lower().replace('_', ' ')} {len(v)}"
                          for k, v in op["by_outcome"].items() if v)
        print(f"{op['operation']}: {parts}")
        for row in op["vectors"]:
            if row["outcome"] in (DISAGREES, ERROR):
                detail = row.get("detail") or (
                    f"expected {json.dumps(row['expected'], ensure_ascii=False)[:300]}, "
                    f"got {json.dumps(row['actual'], ensure_ascii=False)[:300]}")
                print(f"  {row['outcome']} {row['id']}: {detail}")


# ── command line ─────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m conformance.vectors",
                                     description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="check every digest of the frozen suite")
    for name in ("check", "run"):
        p = sub.add_parser(name)
        p.add_argument("--operations", help="comma-separated operations to include")
        p.add_argument("--json", type=Path, help="write the full report here")
        if name == "run":
            p.add_argument("--impl", required=True,
                           help="the command to run per vector; it reads one JSON request on "
                                "stdin and writes one JSON response on stdout")
            p.add_argument("--timeout", type=float, default=20.0)
    sub.add_parser("serve", help="answer one request on stdin with the reference rules")
    args = parser.parse_args(argv)

    if args.command == "serve":
        try:
            request = json.loads(sys.stdin.read())
        except json.JSONDecodeError:
            print(json.dumps({"error": "INVALID_REQUEST"}))
            return 0
        print(json.dumps(answer(request), ensure_ascii=False, sort_keys=True))
        return 0

    if args.command == "verify":
        problems = verify_suite()
        if problems:
            print("[FAIL] the suite's bytes are not the frozen ones:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        manifest = json.loads((SUITE_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
        print(f"[OK] {SUITE}: {len(manifest['files'])} vector files and MANIFEST.json match "
              f"SHA256SUMS (MANIFEST.json sha256 "
              f"{_sha256((SUITE_DIR / 'MANIFEST.json').read_bytes())})")
        return 0

    try:
        operations = load_operations()
    except VectorError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    only = set(args.operations.split(",")) if args.operations else None
    if args.command == "check":
        reference = _reference()
        respond = lambda request: answer(request, reference)  # noqa: E731
    else:
        respond = _subprocess_responder(shlex.split(args.impl), args.timeout)
    rep = report(operations, respond, only)
    if args.json:
        args.json.write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                             encoding="utf-8")
    _print_summary(rep)
    return 1 if _failed(rep) else 0


if __name__ == "__main__":
    sys.exit(main())
