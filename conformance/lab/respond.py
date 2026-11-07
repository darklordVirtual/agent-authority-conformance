"""respond: draft a public reply to a verification challenge from a run's own records.

Everything in the draft is read from SCOPE.json, STATE.json, RUN-PLAN-FROZEN.json and
results/: the pinned commits and file digests, the frozen plan hash, every claim result
and every probe witness. Nothing is recomputed, summed or ranked here, and the draft adds
no statement in anyone else's name. It is written outside the package (under .local/ by
default) so it never changes MANIFEST.json, and it states who drafted it and whether AI
assisted, because public comments prepared with AI say so.
"""

from pathlib import Path

from . import state
from .canonical import read_json
from .errors import GateError
from .independence import BCR, FEDERATION
from .report import INDEPENDENCE_TEXT, display_json, locator_url, track_text

DEFAULT_OUT = ".local/CHALLENGE-RESPONSE.md"
AFTER_RUN = ("RUN", "PACKAGED", "SHARED_PRIVATE", "REVIEWED", "PUBLISHED")


def _status_line(current):
    if current["state"] == "PUBLISHED":
        return "Published through the lab (see STATUS.md in the package)."
    return (f"Lab state `{current['state']}`: not yet published through the lab. Every value below is "
            "recomputable from the pinned bytes, but the run package is not citable as published evidence "
            "until its STATUS.md says PUBLISHED.")


def _claims(scope, results):
    records = results["results/claims.json"]["records"]
    text = {c["id"]: c["text"] for c in scope["claims"]}
    out = ["### Claim results", "",
           "One row per (input, claim). `ESTABLISHED`, `CONTRADICTED` and `NOT_ESTABLISHED` are bounded by the "
           "claim ceiling below; anything else is a non-verdict.", "",
           "| Claim | Input | Input digest | Result | Unresolved obligations |", "|---|---|---|---|---|"]
    for r in records:
        digest = r["evidence"][0].removeprefix("sha256:") if r["evidence"] else "—"
        result = r["result"] or f"{r['execution']} (non-verdict)"
        out.append(f"| `{r['claim']}` | `{r['input']}` | `{digest}` | **{result}** | "
                   f"{', '.join(r.get('unresolved_obligations', [])) or '—'} |")
    out += ["", "Claims:", ""]
    out += [f"- `{cid}`: {t}" for cid, t in text.items()]
    controls = results.get("results/controls.json")
    if controls:
        out += ["", "Negative controls (inputs on which a claim must not be `ESTABLISHED`):", ""]
        label = {True: "discriminated", False: "did not discriminate", None: "not exercised"}
        out += [f"- `{c['claim']}` on `{c['input']}`: {c['observed']} ({label[c['discriminated']]})"
                for c in controls["controls"]]
    return out + [""]


def _probes(scope, results):
    probes = results.get("results/probes.json")
    if not probes:
        return []
    declared = {p["id"]: p for p in scope.get("probes", [])}
    out = ["### Findings", "",
           "Runner-authored probes. A finding is the runner's reproducible observation with a witness anyone "
           "can recompute; it is not a claim result and not a statement by the producer. Assessment levels are "
           "the runner's judgment and are not summed.", ""]
    for n, r in enumerate(probes["records"], start=1):
        p = declared[r["probe"]]
        affects = {True: "yes", False: "no"}.get(r.get("affects_pinned_artifact"), "—")
        out += [f"**F{n}. `{r['probe']}`** · {r['class']} · runner assessment: "
                f"{p['runner_assessment']['level']} · {r['observation'] or r['execution']} · "
                f"affects the pinned artifact: {affects}", "",
                f"*Probed:* {p['text']}", ""]
        if r["execution"] != "COMPLETED":
            out += [f"Non-verdict: {r['verifier_error']['message']}", ""]
            continue
        out += [f"*Observed:* {r['message']}", "",
                f"*Why this level:* {p['runner_assessment']['rationale']}", ""]
        locators = p.get("source_locators", [])
        if locators:
            out += ["*Where (read as data, not executed):*", ""]
            out += [f"- [{loc['path']} L{loc['lines']}]({locator_url(scope['subjects'][loc['subject']], loc)}): "
                    f"{loc['note']}" for loc in locators]
            out.append("")
        out += ["<details><summary>Witness</summary>", "", "```json", display_json(r["witness"]), "```", "",
                "</details>", ""]
        if p.get("remediation"):
            out += [f"*Suggested fix:* {p['remediation']}", ""]
    return out


def _pins(scope):
    out = ["### Pinned bytes", "", "| Subject | Repository | Commit | Files pinned |", "|---|---|---|---|"]
    out += [f"| {i} | {s['repo']} | `{s['commit']}` | {len(s['files_sha256'])} |" for i, s in enumerate(scope["subjects"])]
    out.append("")
    for i, s in enumerate(scope["subjects"]):
        out += [f"<details><summary>Subject {i}: SHA-256 of every pinned file</summary>", "",
                "| File | SHA-256 |", "|---|---|"]
        out += [f"| `{path}` | `{digest}` |" for path, digest in s["files_sha256"].items()]
        out += ["", "</details>", ""]
    return out


def _lab_revision(run_dir):
    """The lab revision of the last successful run attempt, from RUN-CAPTURE.json."""
    path = Path(run_dir) / "RUN-CAPTURE.json"
    if not path.is_file():
        return None
    ok = [a for a in read_json(path).get("attempts", []) if a.get("exit_status") == 0]
    rev = ok[-1].get("procedure_revision", {}) if ok else {}
    if rev.get("source") == "git":
        return (f"AACP commit `{rev['commit']}`"
                + (" with local changes to conformance/lab" if rev.get("lab_modified") else ""))
    return "vendored lab code" if rev.get("source") == "vendored" else None


def _method(scope, plan, current, lab=None):
    label = scope["independence"]
    out = ["### Method", "",
           f"- **Independence:** {INDEPENDENCE_TEXT[label]} Reads as `{FEDERATION[label]}`, {BCR[label]} at most."]
    if scope.get("independence_statement"):
        out.append(f"- **Independence statement:** {scope['independence_statement']}")
    out.append(f"- {track_text(scope)}")
    if scope.get("procedure"):
        out.append(f"- **Procedure:** `{scope['procedure']}`.")
    pre = current.get("preregistered", True)
    published = current.get("plan_published_ref")
    out.append(f"- **Frozen plan SHA-256:** `{current['plan_sha256']}`; "
               + (f"published before execution at {published}." if pre and published
                  else "not preregistered (frozen and run without publishing the hash first)."))
    out.append("- **Checks:** the lab loads only the runner's own modules below (hashes from the frozen plan) "
               "and hands them the pinned subject files as data, as bytes or parsed JSON per input.")
    for path, digest in plan["core"]["run_files"].items():
        out.append(f"  - `{path}` `{digest}`")
    if lab:
        out.append(f"- **Lab:** run executed with {lab} (from RUN-CAPTURE.json); Python "
                   f"{plan['environment']['python']}.")
    for item in scope.get("trust_material", []):
        out.append(f"- **Trust material:** {item}")
    authors = scope.get("verifier_authors") or scope["runner"]["maintainers"]
    out.append(f"- **Who:** checks by {', '.join(authors)}; run operated by {scope['runner']['project']}.")
    return out + [""]


def _ceiling(scope):
    ceiling = scope["claim_ceiling"]
    out = ["### What this does and does not establish", "", "Establishes:", ""]
    out += [f"- {x}" for x in ceiling["establishes"]]
    out += ["", "Does not establish:", ""]
    out += [f"- {x}" for x in ceiling["does_not_establish"]]
    return out + [""]


def _reproduce(scope, scope_ref=None):
    return ["### Reproduce", "",
            "In the run package, `python3 rerun.py` fetches each subject at its pinned commit, verifies every "
            "pinned file hash, recomputes the frozen plan hash and reruns every claim and probe with the "
            "vendored lab code (exit 0 `REPRODUCED`, 1 `DIVERGED`, 2 `NOT_REPRODUCIBLE`).", "",
            "From an AACP checkout, the same run can be operated from its scope:", "",
            "```sh",
            f"python -m conformance.lab init {scope['run_id']}-rerun --template {scope_ref or '<path to this SCOPE.json>'}",
            f"python -m conformance.lab pin {scope['run_id']}-rerun",
            f"python -m conformance.lab freeze {scope['run_id']}-rerun --not-preregistered"
            if scope.get("track") == "self_service" else
            f"python -m conformance.lab freeze {scope['run_id']}-rerun",
            f"python -m conformance.lab run {scope['run_id']}-rerun",
            "```", ""]


def render(run_dir, drafted_by="human", ai_assisted=False, scope_ref=None):
    run_dir = Path(run_dir)
    current = state.load_state(run_dir)
    if current["state"] not in AFTER_RUN:
        raise GateError(f"respond needs a measured run (state {', '.join(AFTER_RUN)}); this run is {current['state']}")
    from .package import verify_run_integrity
    plan = verify_run_integrity(run_dir, current)
    scope = read_json(run_dir / "SCOPE.json")
    if scope["kind"] != "verification":
        raise GateError("respond supports verification runs")
    results = {p.relative_to(run_dir).as_posix(): read_json(p) for p in sorted((run_dir / "results").rglob("*.json"))}
    challenge = scope.get("challenge")
    lines = [f"## Bounded verification: `{scope['run_id']}`", ""]
    if challenge:
        lines += [f"Answering the public verification challenge by {challenge['by']} ({challenge['ref']}). "
                  "The challenge asked to:", ""]
        lines += [f"- {a}" for a in challenge["asked"]]
        lines.append("")
    lines += [f"**Status:** {_status_line(current)}", ""]
    lines += _method(scope, plan, current, _lab_revision(run_dir))
    lines += _claims(scope, results)
    lines += _probes(scope, results)
    lines += _ceiling(scope)
    if challenge and challenge["requests_endorsement"]:
        lines += ["### Endorsement", "",
                  "The challenge asked for endorsement if the claims hold. This response gives none. A verified "
                  "artifact is not an endorsed project, and endorsement is outside every claim ceiling above.", ""]
    lines += _pins(scope)
    lines += _reproduce(scope, scope_ref)
    lines += ["---", "",
              f"Drafted by {drafted_by}; AI-assisted: {'yes' if ai_assisted else 'no'}. Prepared with Agent "
              "Authority Conformance Profiles (AACP) run protocol v0.3; not a certification, ranking or score.", ""]
    return "\n".join(lines)


def write(run_dir, out=None, drafted_by="human", ai_assisted=False, scope_ref=None):
    if drafted_by != "human" and not (isinstance(drafted_by, str) and drafted_by.startswith("agent:")
                                      and len(drafted_by) > len("agent:")):
        raise GateError("--drafted-by must be 'human' or 'agent:<id>'")
    text = render(run_dir, drafted_by, ai_assisted, scope_ref)
    path = Path(out) if out else Path(run_dir) / DEFAULT_OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
