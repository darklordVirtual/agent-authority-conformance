"""AACP controls: run a control binding against a subject and report on A-G.

    python -m conformance.controls run    --binding DIR --subject CHECKOUT --out RESULT.json --run-id ID
    python -m conformance.controls report --binding DIR --result RESULT.json --assessment OUT.json \
                                          --markdown OUT.md [--result-ref PATH]
    python -m conformance.controls compare RESULT_A.json RESULT_B.json

A catalog (controls/aacp-controls-v1/catalog.json) defines project-neutral
controls. A binding (controls/bindings/<id>/) implements probes for one pinned
subject. Three probe kinds are generic and reusable across projects:

  cargo-test    a Rust integration test installed into the subject's crate
  command       any command; OBSERVED when it exits 0 (pytest, go test, npm ...)
  source-check  predicates over subject files (regex, order, JSON values)

A probe observes a weakness when it reproduces it on the pristine subject. A
probe with a declared repair (mutation) discriminates when, with that repair
applied alone, it no longer observes the weakness. Only an executed probe with
an `exact` relationship to an A-G property that is OBSERVED and DISCRIMINATES
yields FAIL. Nothing here ever yields PASS: absence of an observed weakness is
not evidence that a property holds (SPECIFICATION §3, §5).

`run` executes subject code for executable probes. Use a disposable environment.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import platform
import re
import shutil
import subprocess
import sys

from .validation import ROOT, validate_assessment

PROPERTY_NAMES = {
    "A": "Receipt Integrity", "B": "Authority Provenance", "C": "Exact-Call Integrity",
    "D": "Semantic Authority", "E": "Execution-Boundary Integrity", "F": "TOCTOU Resistance",
    "G": "Effect Verification",
}
EXECUTABLE = {"cargo-test", "command"}
RELATIONSHIPS = {"exact", "structural", "partial", "false_analog", "no_mapping"}
CARGO_LINE = re.compile(r"^test (\S+) \.\.\. (ok|FAILED|ignored)$")
REGEX_FLAGS = re.MULTILINE | re.DOTALL


#: Every op eval_predicate knows. load_binding checks a binding against it, so
#: a misspelt op is a BindingError before any probe runs, and not a verdict
#: read off whatever branch the typo happens to reach.
REGEX_OPS = frozenset({"matches", "not_matches", "order"})
JSON_OPS = frozenset({"json_exists", "json_equals", "json_lacks", "json_ne_head"})
PREDICATE_OPS = REGEX_OPS | JSON_OPS


class NonVerdict(Exception):
    """The run, or one probe, could not reach a verdict."""


class BindingError(Exception):
    """The binding itself is malformed."""


# ---------------------------------------------------------------- loading

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repo_rel(path) -> str:
    """Repository-relative path when inside AACP, absolute otherwise."""
    path = pathlib.Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def load_binding(binding_dir: pathlib.Path):
    binding_dir = binding_dir.resolve()
    binding = load_json(binding_dir / "binding.json")
    catalog_path = (ROOT / binding["catalog"]).resolve()
    catalog = load_json(catalog_path)
    controls = {c["id"]: c for c in catalog["controls"]}
    for c in catalog["controls"]:
        nb = c.get("normative_basis")
        if c["property"] is not None and not (
                nb and all(nb.get(k) for k in ("specification", "rationale", "boundary"))):
            raise BindingError(f"{c['id']}: an A-G control needs a normative_basis "
                               "(specification, rationale, boundary)")
    mutations = binding.get("mutations", {})
    seen = set()
    for probe in binding["probes"]:
        pid = probe["id"]
        if pid in seen:
            raise BindingError(f"duplicate probe id {pid}")
        seen.add(pid)
        if probe["control"] not in controls:
            raise BindingError(f"{pid}: unknown control {probe['control']}")
        if probe["relationship"] not in RELATIONSHIPS:
            raise BindingError(f"{pid}: relationship must be one of {sorted(RELATIONSHIPS)}")
        if controls[probe["control"]]["property"] is None and probe["relationship"] != "no_mapping":
            raise BindingError(f"{pid}: control has no A-G property, relationship must be no_mapping")
        if probe["kind"] not in EXECUTABLE | {"source-check"}:
            raise BindingError(f"{pid}: unknown kind {probe['kind']}")
        for field in ("mutation", "sensitivity"):
            ref = probe.get(field)
            if ref is not None and ref not in mutations:
                raise BindingError(f"{pid}: unknown {field} {ref}")
        for pred in probe.get("predicates") or []:
            if pred.get("op") not in PREDICATE_OPS:
                raise BindingError(f"{pid}: unknown predicate op {pred.get('op')!r}; "
                                   f"known: {sorted(PREDICATE_OPS)}")
    for na in binding.get("not_applicable", []):
        if na["control"] not in controls or not na.get("reason"):
            raise BindingError(f"not_applicable entry needs a known control and a reason: {na}")
    return binding_dir, binding, catalog, controls, catalog_path


# ---------------------------------------------------------------- subject

def run_cmd(argv, cwd, env=None):
    proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout + proc.stderr


def expand(argv):
    """`{python}` names the interpreter running AACP, so a binding needs no absolute path."""
    return [sys.executable if a == "{python}" else a for a in argv]


def probe_env():
    """No bytecode cache: a repaired and a restored file must never share a stale .pyc."""
    import os
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def tool_version(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True).stdout.strip() or "UNKNOWN"
    except OSError:
        return "NOT_INSTALLED"


def check_subject(subject_dir: pathlib.Path, subject: dict):
    code, head = run_cmd(["git", "rev-parse", "HEAD"], subject_dir)
    head = head.strip()
    if code != 0:
        raise NonVerdict(f"subject is not a git checkout: {subject_dir}")
    if head != subject["revision"]:
        raise NonVerdict(f"checkout is at {head}, expected {subject['revision']}")
    pristine = {}
    for rel, digest in subject.get("files", {}).items():
        path = subject_dir / rel
        if not path.is_file():
            raise NonVerdict(f"pinned file missing: {rel}")
        data = path.read_bytes()
        if sha256_bytes(data) != digest:
            raise NonVerdict(f"pinned file bytes differ: {rel}")
        pristine[rel] = data
    return head, pristine


def apply_mutation(text: str, mutation: dict) -> str:
    count = text.count(mutation["old"])
    if count != 1:
        raise ValueError(f"anchor occurs {count} times")
    return text.replace(mutation["old"], mutation["new"])


def mutation_edits(mutation: dict) -> list[dict]:
    """A mutation is one edit (`file`, `old`, `new`) or several (`edits`).

    Several edits are needed when a protection is enforced in more than one
    layer: removing one layer alone would leave the probe still refused.
    """
    return mutation["edits"] if "edits" in mutation else [mutation]


def mutated_texts(mutation: dict, read) -> dict[str, str]:
    """Apply every edit in order, per file; ValueError on a non-unique anchor."""
    texts: dict[str, str] = {}
    for edit in mutation_edits(mutation):
        current = texts.get(edit["file"], read(edit["file"]))
        texts[edit["file"]] = apply_mutation(current, edit)
    return texts


# ---------------------------------------------------------------- source checks

def get_path(doc, path: str):
    """Dotted path; `name[]` maps over a list. Returns a value or list of values."""
    values = [doc]
    for part in path.split("."):
        many = part.endswith("[]")
        key = part[:-2] if many else part
        nxt = []
        for v in values:
            if not isinstance(v, dict) or key not in v:
                raise KeyError(path)
            item = v[key]
            if many:
                if not isinstance(item, list):
                    raise KeyError(path)
                nxt.extend(item)
            else:
                nxt.append(item)
        values = nxt
    return values if "[]" in path else values[0]


def region_of(text: str, region):
    if not region:
        return text, 0
    start = text.find(region["start"])
    if start < 0:
        raise NonVerdict(f"region start not found: {region['start']!r}")
    end = text.find(region["end"], start + len(region["start"])) if region.get("end") else len(text)
    if end < 0:
        raise NonVerdict(f"region end not found: {region['end']!r}")
    return text[start:end], start


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def eval_predicate(pred: dict, read, head: str):
    """Return (holds: bool, detail: str). `read(rel)` returns the text of a subject file."""
    op = pred["op"]
    text = read(pred["file"])
    if op not in PREDICATE_OPS:
        raise BindingError(f"unknown predicate op {op}")
    if op in REGEX_OPS:
        body, base = region_of(text, pred.get("region"))
        if op == "order":
            a = re.search(pred["first"], body, REGEX_FLAGS)
            b = re.search(pred["then"], body, REGEX_FLAGS)
            if not a or not b:
                return False, "one of the patterns does not occur"
            return b.start() > a.start(), (f"first at line {line_of(text, base + a.start())}, "
                                           f"then at line {line_of(text, base + b.start())}")
        m = re.search(pred["pattern"], body, REGEX_FLAGS)
        where = f"line {line_of(text, base + m.start())}" if m else "no match"
        return (bool(m), where) if op == "matches" else (not m, where)
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        # A file that is not JSON is something the probe could not read, like a
        # missing file or region. It says nothing about the subject's behaviour.
        raise NonVerdict(f"{pred['file']} is not JSON: {exc.msg} "
                         f"(line {exc.lineno}, column {exc.colno})") from exc
    try:
        value = get_path(doc, pred["path"])
    except KeyError:
        return (False, "path absent") if op != "json_lacks" else (True, "path absent")
    if op == "json_exists":
        return True, "present"
    if op == "json_equals":
        want = sha256_bytes(pred["value_sha256_of"].encode()) if "value_sha256_of" in pred else pred["value"]
        return value == want, f"value {value!r}"
    if op == "json_lacks":
        return pred["value"] not in value, f"{len(value)} entries"
    if op == "json_ne_head":
        return value != head, f"{value!r} vs HEAD {head}"
    raise BindingError(f"unknown predicate op {op}")


def eval_source_check(probe, read, head):
    details = []
    holds_all = True
    for pred in probe["predicates"]:
        holds, detail = eval_predicate(pred, read, head)
        details.append({"op": pred["op"], "file": pred["file"], "holds": holds, "detail": detail})
        holds_all &= holds
    return holds_all, details


# ---------------------------------------------------------------- executable probes

def install_runner_files(binding_dir, subject_dir, runners):
    for runner in runners.values():
        for item in runner.get("install", []):
            dest = subject_dir / item["to"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(binding_dir / item["from"], dest)


def remove_runner_files(subject_dir, runners):
    for runner in runners.values():
        for item in runner.get("install", []):
            (subject_dir / item["to"]).unlink(missing_ok=True)


def cargo_run(subject_dir, runner, tests=None):
    argv = ["cargo", "test", "--locked", "--test", runner["test_target"], "--"]
    argv += ["--exact", "--test-threads=1", *tests] if tests else ["--test-threads=1"]
    _, out = run_cmd(argv, subject_dir / runner["crate"])
    statuses = {}
    for raw in out.splitlines():
        m = CARGO_LINE.match(raw.strip())
        if m:
            statuses[m.group(1)] = m.group(2)
    built = "Running tests/" in out or bool(statuses)
    return built, statuses


def command_run(subject_dir, probe):
    code, _ = run_cmd(expand(probe["argv"]), subject_dir / probe.get("cwd", "."), env=probe_env())
    return code


def command_result(probe, code):
    """0 observes. With `not_observed_exit` (pytest: [1]) any other code is a probe error,
    so a crashed or uncollected probe is never read as a protection that held."""
    if code == 0:
        return "OBSERVED"
    allowed = probe.get("not_observed_exit")
    if allowed is not None and code not in allowed:
        return "NON_VERDICT"
    return "NOT_OBSERVED"


def run_setup(subject_dir, runners, record):
    """Runner setup commands (dependency install), once, before any executable probe."""
    for name, runner in sorted(runners.items()):
        for argv in runner.get("setup", []):
            code, out = run_cmd(expand(argv), subject_dir, env=probe_env())
            record["setup"].append({"runner": name, "argv": argv, "exit": code})
            if code != 0:
                raise NonVerdict(f"setup failed ({name}): {' '.join(argv)}: {out[-400:]}")


# ---------------------------------------------------------------- run

def run(args):
    binding_dir, binding, catalog, controls, catalog_path = load_binding(args.binding)
    expected = load_json(binding_dir / "expected.json")
    subject = binding["subject"]
    subject_dir = args.subject.resolve()
    runners = binding.get("runners", {})
    mutations = binding.get("mutations", {})

    record = {
        "schema": "aacp-control-run-v1",
        "run_id": args.run_id,
        "started_at_utc": now(),
        "operator": args.operator,
        "independence": args.independence,
        "binding": binding["binding_id"],
        "subject": {k: subject[k] for k in ("name", "version", "repository", "revision")},
        "procedure": {
            "runner": "conformance/controls.py",
            "runner_sha256": sha256_bytes(pathlib.Path(__file__).read_bytes()),
            "catalog": repo_rel(catalog_path),
            "catalog_version": catalog["version"],
            "catalog_sha256": sha256_bytes(catalog_path.read_bytes()),
            "binding_sha256": {repo_rel(p): sha256_bytes(p.read_bytes())
                               for p in sorted(binding_dir.rglob("*")) if p.is_file()
                               and "results" not in p.relative_to(binding_dir).parts},
            "aacp_revision": run_cmd(["git", "rev-parse", "HEAD"], ROOT)[1].strip() or "UNKNOWN",
            "aacp_tree_clean": run_cmd(["git", "status", "--porcelain", "--", "conformance/controls.py",
                                        "controls"], ROOT)[1].strip() == "",
        },
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            **({"rustc": tool_version(["rustc", "--version"]), "cargo": tool_version(["cargo", "--version"])}
               if "cargo" in runners else {}),
        },
        "setup": [],
        "probes": {},
        "not_applicable": binding.get("not_applicable", []),
        "non_verdict_errors": [],
    }

    pristine = {}
    try:
        head, pristine = check_subject(subject_dir, subject)

        def read_pristine(rel):
            if rel in pristine:
                return pristine[rel].decode("utf-8")
            path = subject_dir / rel
            if not path.is_file():
                raise NonVerdict(f"file not found: {rel}")
            return path.read_text(encoding="utf-8")

        for probe in binding["probes"]:
            entry = {"control": probe["control"], "kind": probe["kind"], "relationship": probe["relationship"],
                     "origin": probe["origin"], "mutation": probe.get("mutation")}
            record["probes"][probe["id"]] = entry

        # Source checks: pristine, then each declared repair in memory.
        for probe in binding["probes"]:
            if probe["kind"] != "source-check":
                continue
            entry = record["probes"][probe["id"]]
            try:
                observed, details = eval_source_check(probe, read_pristine, head)
                entry["result"] = "OBSERVED" if observed else "NOT_OBSERVED"
                entry["predicates"] = details
                entry["discrimination"] = "NOT_RUN"
                if probe.get("mutation") and observed:
                    mut = mutations[probe["mutation"]]
                    try:
                        mutated = mutated_texts(mut, read_pristine)
                    except ValueError as exc:
                        entry["discrimination"] = "ANCHOR_ERROR"
                        entry["discrimination_detail"] = str(exc)
                    else:
                        still, _ = eval_source_check(
                            probe, lambda rel: mutated[rel] if rel in mutated else read_pristine(rel), head)
                        entry["discrimination"] = "DOES_NOT_DISCRIMINATE" if still else "DISCRIMINATES"
                if probe.get("sensitivity"):
                    entry["sensitivity"] = "NOT_RUN"
                if probe.get("sensitivity") and not observed:
                    mut = mutations[probe["sensitivity"]]
                    try:
                        weakened = mutated_texts(mut, read_pristine)
                    except ValueError as exc:
                        entry["sensitivity"] = "ANCHOR_ERROR"
                        entry["sensitivity_detail"] = str(exc)
                    else:
                        seen, _ = eval_source_check(
                            probe, lambda rel: weakened[rel] if rel in weakened else read_pristine(rel), head)
                        entry["sensitivity"] = "SENSITIVE" if seen else "INSENSITIVE"
            except NonVerdict as exc:
                entry["result"] = "NON_VERDICT"
                entry["detail"] = str(exc)

        executable = [p for p in binding["probes"] if p["kind"] in EXECUTABLE]
        if executable:
            install_runner_files(binding_dir, subject_dir, runners)
            try:
                run_setup(subject_dir, runners, record)
                run_executable(executable, record, subject_dir, runners, mutations, pristine)
            finally:
                for rel, data in pristine.items():
                    (subject_dir / rel).write_bytes(data)
                remove_runner_files(subject_dir, runners)
        check_subject(subject_dir, subject)  # restored exactly
    except NonVerdict as exc:
        record["non_verdict_errors"].append(str(exc))

    record["expectations"] = compare_expected(record, expected)
    record["verdict"] = ("NON_VERDICT" if record["non_verdict_errors"] else
                         "EXPECTATIONS_MET" if record["expectations"]["met"] else "EXPECTATIONS_NOT_MET")
    record["finished_at_utc"] = now()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for e in record["probes"].values():
        counts[e.get("result", "NOT_RUN")] = counts.get(e.get("result", "NOT_RUN"), 0) + 1
    print(f"{record['verdict']}: {counts} -> {args.out}")
    return 0 if record["verdict"] == "EXPECTATIONS_MET" else 1


def run_executable(probes, record, subject_dir, runners, mutations, pristine):
    cargo = [p for p in probes if p["kind"] == "cargo-test"]
    if cargo:
        runner = runners["cargo"]
        built, statuses = cargo_run(subject_dir, runner)
        if not built:
            raise NonVerdict("cargo baseline did not build")
        for p in cargo:
            st = statuses.get(p["test"])
            e = record["probes"][p["id"]]
            e["test"] = p["test"]
            e["result"] = {"ok": "OBSERVED", "FAILED": "NOT_OBSERVED"}.get(st, "NON_VERDICT")
            e["baseline_status"] = st or "MISSING"
    for p in probes:
        if p["kind"] == "command":
            e = record["probes"][p["id"]]
            e["argv"] = p["argv"]
            code = command_run(subject_dir, p)
            e["result"] = command_result(p, code)
            e["baseline_exit"] = code

    # Discrimination: a repair applied alone must make an OBSERVED probe stop observing.
    # Sensitivity: a weakening applied alone must make a NOT_OBSERVED probe observe.
    # Grouped by mutation so each one is applied once.
    for field, when, good, bad in (("mutation", "OBSERVED", "DISCRIMINATES", "DOES_NOT_DISCRIMINATE"),
                                   ("sensitivity", "NOT_OBSERVED", "SENSITIVE", "INSENSITIVE")):
        out_key = "discrimination" if field == "mutation" else "sensitivity"
        groups = {}
        for p in probes:
            e = record["probes"][p["id"]]
            if not p.get(field):
                if field == "mutation":
                    e[out_key] = "NOT_RUN"
                continue
            if e["result"] != when:
                e[out_key] = "NOT_RUN"
            else:
                groups.setdefault(p[field], []).append(p)
        for ref, group in sorted(groups.items()):
            apply_and_probe(ref, group, out_key, good, bad, record, subject_dir, runners, mutations, pristine)


def apply_and_probe(ref, group, out_key, good, bad, record, subject_dir, runners, mutations, pristine):
    """Apply one mutation, rerun its probes, restore the pristine file.

    For a repair (`good` = DISCRIMINATES) the probe must stop observing; for a
    weakening (`good` = SENSITIVE) it must start observing.
    """
    mut = mutations[ref]
    want_observed = good == "SENSITIVE"
    for edit in mutation_edits(mut):
        if edit["file"] not in pristine:
            raise NonVerdict(f"mutation {ref} targets an unpinned file {edit['file']}")
    try:
        mutated = mutated_texts(mut, lambda rel: pristine[rel].decode("utf-8"))
    except ValueError as exc:
        for p in group:
            record["probes"][p["id"]][out_key] = "ANCHOR_ERROR"
            record["probes"][p["id"]][out_key + "_detail"] = str(exc)
        return
    for rel, text in mutated.items():
        (subject_dir / rel).write_text(text, encoding="utf-8")
    try:
        cargo_group = [p for p in group if p["kind"] == "cargo-test"]
        if cargo_group:
            built, statuses = cargo_run(subject_dir, runners["cargo"], [p["test"] for p in cargo_group])
            for p in cargo_group:
                e = record["probes"][p["id"]]
                st = statuses.get(p["test"])
                e["mutated_status" if out_key == "discrimination" else "sensitivity_status"] = st or "MISSING"
                observed = st == "ok"
                e[out_key] = ("BUILD_ERROR" if not built else
                              good if observed == want_observed else bad)
        for p in group:
            if p["kind"] == "command":
                e = record["probes"][p["id"]]
                code = command_run(subject_dir, p)
                e["mutated_exit" if out_key == "discrimination" else "sensitivity_exit"] = code
                if command_result(p, code) == "NON_VERDICT":
                    e[out_key] = "PROBE_ERROR"
                else:
                    e[out_key] = good if (code == 0) == want_observed else bad
    finally:
        for rel in mutated:
            (subject_dir / rel).write_bytes(pristine[rel])


def compare_expected(record, expected):
    mismatches = {}
    for pid, want in expected["probes"].items():
        got = record["probes"].get(pid)
        if got is None:
            mismatches[pid] = {"expected": want, "observed": "MISSING"}
            continue
        obs = {k: got.get(k) for k in want}
        if obs != want or not {"result", "discrimination"} <= set(want):
            mismatches[pid] = {"expected": want, "observed": obs}
    for pid in record["probes"]:
        if pid not in expected["probes"]:
            mismatches[pid] = {"expected": "MISSING", "observed": "unexpected probe"}
    return {"met": not mismatches, "mismatches": mismatches}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- report

def counted(probe_entry, controls, prop):
    c = controls[probe_entry["control"]]
    return (c["property"] == prop and probe_entry["relationship"] == "exact"
            and probe_entry["kind"] in EXECUTABLE and probe_entry.get("result") == "OBSERVED"
            and probe_entry.get("discrimination") == "DISCRIMINATES")


def build_assessment(binding, controls, result, result_ref, binding_rel):
    if result["non_verdict_errors"]:
        raise NonVerdict("cannot report on a run with non-verdict errors: " + "; ".join(result["non_verdict_errors"]))
    probes = result["probes"]
    defs = {p["id"]: p for p in binding["probes"]}
    mutations = binding.get("mutations", {})
    oos = binding.get("out_of_scope_properties", {})
    caveats = binding.get("property_caveats", {})
    na = {n["control"]: n["reason"] for n in binding.get("not_applicable", [])}
    rows = []
    for prop, name in PROPERTY_NAMES.items():
        mine = {pid: e for pid, e in probes.items() if controls[e["control"]]["property"] == prop}
        fails = {pid: e for pid, e in mine.items() if counted(e, controls, prop)}
        others = {pid: e for pid, e in mine.items() if pid not in fails}
        na_here = sorted(c for c in na if controls[c]["property"] == prop)
        if prop in oos:
            row = {"id": prop, "property": name, "status": "OUT_OF_SCOPE", "evidence_tier": "NONE",
                   "claimed_status": "not claimed", "reasoning": oos[prop],
                   "caveat": "OUT_OF_SCOPE records the implementer's stated claim boundary and is not negative credit.",
                   "evidence": []}
        elif fails:
            parts, bounds = [], []
            for pid, e in sorted(fails.items()):
                c = controls[e["control"]]
                m = mutations[e["mutation"]]
                parts.append(f"{e['control']} ({c['title']}) is OBSERVED by probe {pid} and discriminates "
                             f"under repair {e['mutation']} ({m['repair']}). Why this is {prop}: "
                             f"{c['normative_basis']['rationale']}")
                bounds.append(f"{e['control']} boundary: {c['normative_basis']['boundary']}")
            row = {"id": prop, "property": name, "status": "FAIL", "evidence_tier": "RESOLVED",
                   "claimed_status": binding.get("claimed_status", "not supplied by implementer"),
                   "reasoning": " ".join(parts),
                   "caveat": " ".join([caveats.get(prop, "A FAIL row establishes only the observed weaknesses "
                                                       "under the probed conditions."), *sorted(set(bounds))]),
                   "evidence": []}
            for pid, e in sorted(fails.items()):
                d = defs[pid]
                row["evidence"].append({
                    "kind": "test",
                    "reference": f"{binding_rel}/{d.get('reference', d.get('test', pid))}",
                    "command": "python -m conformance.controls run --binding "
                               f"{binding_rel} --subject <checkout> --out <result.json> --run-id <id>",
                    "description": f"Probe {pid} for {e['control']}: {d['description']}"})
                if d.get("code"):
                    row["evidence"].append({"kind": "code", "reference": d["code"],
                                            "revision": binding["subject"]["revision"],
                                            "description": f"Subject code exercised by probe {pid}."})
            row["evidence"].append({"kind": "artifact", "reference": result_ref,
                                    "description": "Result record of the run this assessment was generated from."})
        else:
            row = {"id": prop, "property": name, "status": "UNTESTED", "evidence_tier": "NONE",
                   "reasoning": "No executed, exact, discriminating probe observed a weakness for this property.",
                   "caveat": "UNTESTED records absent evidence, not failure. AACP controls never yield PASS; "
                             "a PASS needs an assessor's direct evidence (SPECIFICATION §5).",
                   "evidence": []}
        extra = []
        for pid, e in sorted(others.items()):
            why = describe_not_counted(e)
            extra.append(f"{pid} ({e['control']}, {e['relationship']}, {e['kind']}): {why}")
        for c in na_here:
            extra.append(f"{c}: NOT_APPLICABLE ({na[c]})")
        if extra:
            key = "caveat" if row["status"] == "FAIL" else "reasoning"
            row[key] = row[key] + " Also: " + "; ".join(extra) + "."
        rows.append(row)

    notes = ["No aggregate is implied. Per SPECIFICATION §7 the rows are not commensurable and must not be "
             "combined into a score or ranking.",
             "Generated by `python -m conformance.controls report` from catalog "
             f"{result['procedure']['catalog']} v{result['procedure']['catalog_version']} and binding "
             f"{binding_rel}. FAIL requires an executed probe with an exact relationship that is OBSERVED and "
             "DISCRIMINATES under its declared repair."]
    outside = [(pid, e) for pid, e in sorted(probes.items()) if controls[e["control"]]["property"] is None]
    if outside:
        notes.append("Controls outside A-G: " + "; ".join(
            f"{e['control']} {controls[e['control']]['title']} via {pid} ({e['kind']}): {e.get('result')}"
            f"{', ' + e['discrimination'] if e.get('discrimination') not in (None, 'NOT_RUN') else ''}"
            for pid, e in outside) + ".")
    notes.extend(binding.get("notes", []))
    notes.append(f"Reproduce: python -m conformance.controls run --binding {binding_rel} --subject <checkout at "
                 f"{binding['subject']['revision']}> --out <result.json> --run-id <id>.")
    return {
        "spec_version": "0.1",
        "system": binding["subject"]["name"],
        "system_version": binding["subject"]["version"],
        "revision": binding["subject"]["revision"],
        "assessed_at": result["started_at_utc"][:10],
        "assessor": binding.get("assessor", "UNKNOWN"),
        "scope": binding["scope"],
        "properties": rows,
        "notes": notes,
    }


def describe_not_counted(e):
    if e.get("result") == "NOT_OBSERVED" and e.get("sensitivity") == "SENSITIVE":
        return "NOT_OBSERVED by a probe shown to be sensitive (it observes the weakness when the protection is removed); not a PASS"
    if e.get("result") == "NOT_OBSERVED" and e.get("sensitivity") not in (None, "NOT_RUN"):
        return f"NOT_OBSERVED, but sensitivity is {e['sensitivity']}, so this says nothing about the weakness"
    if e.get("result") != "OBSERVED":
        return f"{e.get('result')}; not a PASS"
    if e["kind"] not in EXECUTABLE:
        return "OBSERVED by static source check only" + (
            f", {e['discrimination']}" if e.get("discrimination") not in (None, "NOT_RUN") else "")
    if e["relationship"] != "exact":
        return f"OBSERVED, {e.get('discrimination')}, but the relationship is {e['relationship']}"
    return f"OBSERVED but {e.get('discrimination')}"


def build_markdown(binding, controls, result, assessment, binding_rel, result_ref):
    s = binding["subject"]
    out = [f"# AACP control report: {s['name']} {s['version']}", "",
           f"Generated by `python -m conformance.controls report` from result `{result['run_id']}`. "
           "Do not edit by hand; regenerate.", "",
           f"- Subject: [{s['repository']}]({s['repository']}) at `{s['revision']}`",
           f"- Binding: [`{binding_rel}`](../../{binding_rel}), catalog v{result['procedure']['catalog_version']}",
           f"- Run: `{result['run_id']}`, independence `{result['independence']}`, operator {result['operator']}",
           f"- Result record: [`{result_ref}`](../../{result_ref}), verdict `{result['verdict']}`",
           f"- Assessment (schema v0.1): [`examples/{binding['binding_id']}.json`](../../examples/{binding['binding_id']}.json)",
           "", "## Evidence provenance", "",
           "The run's independence classification is on the Run line above. `AUTHOR_RUN` means the assessor wrote the probes and repairs and ran them. A `REPRODUCTION` "
           "reruns the same probes on another host; it confirms the result is repeatable, not that the probes "
           "are right. Neither is an independent security review, and none has been reviewed by the implementer "
           "unless the notes say so.",
           "", "## A-G", "", "| Property | Status | Controls counted |", "| :--- | :--- | :--- |"]
    for row in assessment["properties"]:
        ids = sorted({e["control"] for pid, e in result["probes"].items() if counted(e, controls, row["id"])})
        out.append(f"| {row['id']} {row['property']} | **{row['status']}** | {', '.join(ids) or '-'} |")
    sens = any("sensitivity" in e for e in result["probes"].values())
    out += ["", "Rows are not commensurable and are not combined (SPECIFICATION §7). AACP controls never "
            "yield PASS.", "", "## Probes", ""]
    if sens:
        out += ["Discrimination: the weakness disappears when it alone is repaired. Sensitivity: a probe that "
                "did not observe the weakness observes it when the protection alone is removed, so its "
                "NOT_OBSERVED result is meaningful.", ""]
    out += ["| Probe | Control | Property | Relationship | Origin | Kind | Result | Discrimination |"
            + (" Sensitivity |" if sens else ""),
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |" + (" :--- |" if sens else "")]
    for pid, e in sorted(result["probes"].items()):
        c = controls[e["control"]]
        out.append(f"| {pid} | {e['control']} {c['title']} | {c['property'] or '-'} | {e['relationship']} | "
                   f"{e['origin']} | {e['kind']} | {e.get('result')} | {e.get('discrimination')} |"
                   + (f" {e.get('sensitivity', '-')} |" if sens else ""))
    if result.get("not_applicable"):
        out += ["", "## Not applicable", ""]
        out += [f"- {n['control']}: {n['reason']}" for n in result["not_applicable"]]
    counted_ids = sorted({e["control"] for e in result["probes"].values()
                          if any(counted(e, controls, p) for p in PROPERTY_NAMES)})
    if counted_ids:
        out += ["", "## Normative basis of counted controls", "",
                "Why each counted control bears on its property, and where it would not.", ""]
        for cid in counted_ids:
            c, nb = controls[cid], controls[cid]["normative_basis"]
            out += [f"### {cid} {c['title']} ({c['property']})", "", f"- Specification: {nb['specification']}",
                    f"- Rationale: {nb['rationale']}", f"- Boundary: {nb['boundary']}", ""]
    out += ["", "## Assessment detail", ""]
    for row in assessment["properties"]:
        out += [f"### {row['id']} {row['property']}: {row['status']}", "", row["reasoning"], "",
                f"*Caveat:* {row['caveat']}", ""]
    out += ["## Notes", ""] + [f"- {n}" for n in assessment["notes"]] + [""]
    return "\n".join(out)


def report(args):
    binding_dir, binding, _, controls, _ = load_binding(args.binding)
    result = load_json(args.result)
    binding_rel = repo_rel(binding_dir)
    result_ref = args.result_ref or repo_rel(args.result)
    assessment = build_assessment(binding, controls, result, result_ref, binding_rel)
    validate_assessment(assessment)
    md = build_markdown(binding, controls, result, assessment, binding_rel, result_ref)
    if args.check:
        old_a = load_json(args.assessment)
        old_md = pathlib.Path(args.markdown).read_text(encoding="utf-8")
        same_a = strip_run(old_a) == strip_run(assessment)
        same_md = strip_md(old_md) == strip_md(md)
        print(f"assessment {'unchanged' if same_a else 'DIFFERS'}; markdown {'unchanged' if same_md else 'DIFFERS'}")
        return 0 if same_a and same_md else 1
    pathlib.Path(args.assessment).write_text(json.dumps(assessment, indent=2) + "\n", encoding="utf-8")
    pathlib.Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.markdown).write_text(md, encoding="utf-8")
    print(f"wrote {args.assessment} and {args.markdown}")
    return 0


def strip_run(assessment):
    return {k: v for k, v in assessment.items() if k != "assessed_at"}


def strip_md(md):
    return "\n".join(l for l in md.splitlines()
                     if not l.startswith(("Generated by", "- Run:", "- Result record:")))


def compare(args):
    a, b = load_json(args.a), load_json(args.b)
    keys = ("control", "kind", "relationship", "result", "discrimination", "sensitivity")
    pa = {k: {f: v.get(f) for f in keys} for k, v in a["probes"].items()}
    pb = {k: {f: v.get(f) for f in keys} for k, v in b["probes"].items()}
    diff = {k: {"a": pa.get(k), "b": pb.get(k)} for k in sorted(set(pa) | set(pb)) if pa.get(k) != pb.get(k)}
    same = not diff and a["subject"] == b["subject"]
    print(json.dumps({"same_findings": same, "differences": diff}, indent=2))
    return 0 if same else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--binding", type=pathlib.Path, required=True)
    r.add_argument("--subject", type=pathlib.Path, required=True)
    r.add_argument("--out", type=pathlib.Path, required=True)
    r.add_argument("--run-id", required=True)
    r.add_argument("--operator", default="UNKNOWN")
    r.add_argument("--independence", default="AUTHOR_RUN",
                   choices=["AUTHOR_RUN", "REPRODUCTION", "SECOND_IMPLEMENTATION", "INDEPENDENT_IMPLEMENTATION"])
    p = sub.add_parser("report")
    p.add_argument("--binding", type=pathlib.Path, required=True)
    p.add_argument("--result", type=pathlib.Path, required=True)
    p.add_argument("--assessment", type=pathlib.Path, required=True)
    p.add_argument("--markdown", type=pathlib.Path, required=True)
    p.add_argument("--result-ref", help="repository path recorded as the result evidence")
    p.add_argument("--check", action="store_true", help="compare with the existing files instead of writing")
    c = sub.add_parser("compare")
    c.add_argument("a", type=pathlib.Path)
    c.add_argument("b", type=pathlib.Path)
    args = ap.parse_args(argv)
    try:
        return {"run": run, "report": report, "compare": compare}[args.cmd](args)
    except (BindingError, NonVerdict) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
