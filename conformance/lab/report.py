"""Markdown for REPORT, STATUS, NOTICE and REPRODUCE. Nothing is ever aggregated."""

from .canonical import sha256_json
from .independence import BCR, FEDERATION, per_claim

INDEPENDENCE_TEXT = {
    "SELF_RUN": "SELF_RUN. The runner measured its own project; this is not independent evidence.",
    "REPRODUCTION": "REPRODUCTION. The runner reran the producer's own verifier; this establishes "
                    "reproducibility, not implementation independence.",
    "SECOND_IMPLEMENTATION": "SECOND_IMPLEMENTATION. A reproduction made with knowledge of the "
                             "producer's code; not independent verification.",
    "INDEPENDENT_IMPLEMENTATION": "INDEPENDENT_IMPLEMENTATION. The runner's own implementation; "
                                  "see the independence statement.",
}
STATUS_TEXT = {
    "PRIVATE": "PRIVATE. Shared with the named maintainers for review. Not published and not "
               "citable as public evidence.",
    "PUBLISHED": "PUBLISHED. Every named approver approved publication (see CONSENT.json). The "
                 "measured results are unchanged since delivery.",
    "WITHHELD": "WITHHELD. Publication was declined. Not citable as public evidence.",
    "PUBLISHED_SELF_SERVICE": "PUBLISHED (self-service, unreviewed). Published by the runner under the "
                              "producer's open verification offer; not reviewed and not endorsed.",
}
LIMITS = (
    "Verification is not endorsement, adoption, dependency or transfer of ownership.",
    "A survivor means this corpus did not distinguish that fault on the declared projection; "
    "it is not a checker defect.",
    "Crash kills are listed separately and are not projection changes.",
    "Nothing is summed across rows, fault sets or claims, and there is no percentage headline.",
    "Local execution is not network isolation.",
    "Until STATUS.md says PUBLISHED, this report is not citable as public evidence.",
)


def _bullets(items):
    items = list(items)
    return "\n".join(f"- {item}" for item in items) if items else "- none"


def render_report(scope, plan, results, conditions=None, preregistered=True):
    lines = [f"# {scope['run_id']}", "",
             f"**Independence:** {INDEPENDENCE_TEXT[scope['independence']]}", "",
             f"Reads as `{FEDERATION[scope['independence']]}` in federation-run-v1 and "
             f"{BCR[scope['independence']]} in BCR terms.", ""]
    if scope.get("independence_statement"):
        lines += [f"**Independence statement:** {scope['independence_statement']}", ""]
    if scope.get("previous_run"):
        prev = scope["previous_run"]
        lines += [f"Follow-up of `{prev['run_id']}` (plan `{prev['plan_sha256']}`); earlier results are unchanged.", ""]
    if scope.get("track") == "self_service":
        ref = scope["offer"]
        lines += [f"**Track:** self-service under the producer's offer `{ref['offer_id']}` "
                  f"({ref['repo']} at `{ref['commit']}`, `{ref['path']}` SHA-256 `{ref['sha256']}`). "
                  "No per-run human gate; inputs are admitted by the offer.", ""]
    else:
        lines += ["**Track:** manual. Scope agreement, run authorisation and admission are in CONSENT.json.", ""]
    lines += ["Publication status: see STATUS.md. Agreement: " + str(scope.get("agreement_ref")), "",
              "## Pinned inputs", "", "| Project | Repository | Commit | Licence |", "|---|---|---|---|"]
    lines += [f"| {s['project']} | {s['repo']} | `{s['commit']}` | {s['license']} |" for s in scope["subjects"]]
    lines += ["", f"Frozen plan SHA-256: `{sha256_json(plan['core'])}` (Python {plan['environment']['python']}).",
              "", f"Preregistered: {'yes' if preregistered else 'no'}.",
              "", "## Claim ceiling", "", "Establishes:", "", _bullets(scope["claim_ceiling"]["establishes"]),
              "", "Does not establish:", "", _bullets(scope["claim_ceiling"]["does_not_establish"]), ""]
    if scope["kind"] == "adequacy":
        lines += _adequacy_sections(scope, results)
    else:
        lines += _verification_sections(results)
    lines += _claim_ceiling_sections(scope)
    lines += _independence_section(scope)
    lines += _condition_sections(scope, conditions or [])
    lines += ["## Limits", "", _bullets(LIMITS), "",
              "Prepared with the Agent Authority Conformance lab; see CONSENT.json for who agreed to what.", ""]
    return "\n".join(lines)


def _adequacy_sections(scope, results):
    out = []
    for row in scope["rows"]:
        r = results[f"results/{row['id']}.json"]
        c = r["controls"]
        out += [f"## Row `{row['id']}`: {r['status']}", "",
                f"Projection: {', '.join(f'`{p}`' for p in r['projection'])}. Engine: `{r['engine']['name']}`.", "",
                f"Controls: positive `{c['positive']['fault_id']}` {c['positive']['outcome']}; "
                f"inert `{c['inert']['fault_id']}` moved {c['inert']['moved']}, crashed {c['inert']['crashed']}.", ""]
        for name, counts in r["counts_by_set"].items():
            kind = next(m["set"] for m in r["mutants"] if m["set_name"] == name)
            out += [f"Fault set `{name}` ({kind}):", "", "| killed | killed_crash | survived | not_measured |",
                    "|---:|---:|---:|---:|",
                    f"| {counts['killed']} | {counts['killed_crash']} | {counts['survived']} | {counts['not_measured']} |", ""]
        survivors = [m for m in r["mutants"] if m["outcome"] == "survived"]
        crashes = [m for m in r["mutants"] if m["outcome"] == "killed_crash"]
        unmapped = [m for m in r["mutants"] if m["outcome"] == "not_measured"]
        out += ["Survivors (corpus discrimination limits, not checker defects):", "",
                _bullets(f"`{m['fault_id']}` ({m['set_name']}, {m['class']})" for m in survivors), "",
                "Crash kills:", "", _bullets(f"`{m['fault_id']}` ({m['set_name']})" for m in crashes), ""]
        if unmapped:
            out += ["Not measured (engine verdict kept as reported):", "",
                    _bullets(f"`{m['fault_id']}`: {m['engine_verdict']}" for m in unmapped), ""]
        cross = results.get(f"results/cross-check/{row['id']}.json")
        if cross:
            out += [f"Engine cross-check ({cross['primary']} vs {cross['secondary']}): "
                    f"{len(cross['disagreements'])} disagreement(s). This is an engine finding only.", ""]
    return out


def _verification_sections(results):
    records = results["results/claims.json"]["records"]
    out = ["## Per-claim results", "",
           "| Input | Claim | Execution | Result | Reads | Unresolved obligations |", "|---|---|---|---|---|---|"]
    for r in records:
        result = r["result"] or f"— ({r['verifier_error']['code']})"
        out.append(f"| {r['input']} | {r['claim']} | {r['execution']} | {result} | "
                   f"{', '.join(r.get('reads', []))} | {', '.join(r.get('unresolved_obligations', []))} |")
    agree = results.get("results/agreement.json")
    if agree:
        out += ["", "## Agreement with the producer's expectations (not a result)", "", agree["note"], "",
                "| Input | Claim | Ours | Producer | Agree |", "|---|---|---|---|---|"]
        out += [f"| {a['input']} | {a['claim']} | {a['ours']} | {a['producer']} | {'yes' if a['agree'] else 'no'} |"
                for a in agree["rows"]]
    return out + [""]


def _claim_ceiling_sections(scope):
    claims = [c for c in scope.get("claims", []) if "claim_ceiling" in c]
    if not claims:
        return []
    out = ["## Per-claim ceilings", ""]
    for c in claims:
        out += [f"`{c['id']}` establishes:", "", _bullets(c["claim_ceiling"]["establishes"]), "",
                f"`{c['id']}` does not establish:", "", _bullets(c["claim_ceiling"]["does_not_establish"]), ""]
    return out


def _independence_section(scope):
    rows = per_claim(scope)
    authored = scope.get("runner_authored") or []
    out = ["## Independence per claim", "",
           "Runner-authored material: " + (", ".join(authored) if authored else "none declared") + ".", "",
           "| Claim | Independent | Basis |", "|---|---|---|"]
    out += [f"| {cid} | {'yes' if v['independent'] else 'no'} | {v['reason']} |" for cid, v in rows.items()]
    return out + [""]


def _condition_sections(scope, conditions):
    if not conditions:
        return []
    ids = [c["id"] for c in scope.get("claims", [])] + [r["id"] for r in scope.get("rows", [])]
    out = ["## Claim conditions", "",
           "Conditions attached to scope confirmations. They qualify the ceiling of the named claims.", ""]
    for claim_id in ids:
        attached = [c for c in conditions if claim_id in c["claims"]]
        if attached:
            out += [f"`{claim_id}`:", "", _bullets(f"{c['text']} (scope confirmation by {c['who']})"
                                                   for c in attached), ""]
    return out


def render_status(status, notes=()):
    text = f"# Status\n\n**{STATUS_TEXT[status]}**\n"
    return text + ("\n" + _bullets(notes) + "\n" if notes else "")


def render_notice(scope):
    parts = ["NOTICE", ""]
    for i, s in enumerate(scope["subjects"]):
        parts += [f"Subject {i}: {s['project']} ({s['repo']} at {s['commit']}).",
                  f"Attribution: {s['attribution']}.",
                  f"Licence: {s['license']}. Quoted or mutated material from this subject keeps these terms; "
                  f"see UPSTREAM-LICENSE-{i}.txt when present.", ""]
    parts += [f"Runner: {scope['runner']['project']}. This package adds no licence to quoted upstream material.",
              "Fault definitions keep the author and reference recorded in their source field.",
              "The vendored lab/ code is Agent Authority Conformance, Apache-2.0.", ""]
    return "\n".join(parts)


def render_reproduce(scope, plan):
    lines = ["# Reproduce", "",
             f"Recorded with Python {plan['environment']['python']}. Any Python 3.12 or newer can rerun; "
             "a different minor version is reported as a warning.", "",
             "```sh", "python3 rerun.py", "```", "",
             "`rerun.py` verifies MANIFEST.json, fetches each subject at its pinned commit (the only network "
             "step, before anything executes), verifies every pinned file hash, recomputes the frozen plan "
             "hash, reruns every row or claim with the vendored lab code and compares with results/.", "",
             "Exit 0 REPRODUCED, 1 DIVERGED (details in reruns/), 2 NOT_REPRODUCIBLE.", ""]
    if scope["kind"] == "adequacy" and "corpus_adequacy" in (scope["engine"]["name"], scope["engine"].get("cross_check")):
        lines += ["The corpus_adequacy engine needs a checkout of corpus-adequacy at the pinned commit; "
                  "set AAC_CORPUS_ADEQUACY to its path.", ""]
    lines += ["A different subject commit is not a rerun: start a follow-up run with "
              "`python -m conformance.lab init <new_id> --follow-up <run_id> --commit <sha>`.", ""]
    return "\n".join(lines)
