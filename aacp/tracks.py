"""`aacp next` and `aacp export map` over lab runs (see docs/FEDERATION-TRACKS.md).

`next` lists what a run is waiting for: mechanical steps the operator can run, and
human statements only the named party can make. It never proposes an event on
another person's behalf. `export map` writes one evidence record in the shape of the
systems-map prototype (aeoess/agent-governance-vocabulary#187); it never writes owner
confirmation, never opens a pull request, and discloses no result of an unpublished run.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from conformance.lab import consent, independence
from conformance.lab.canonical import read_json
from conformance.lab.errors import GateError
from conformance.lab.state import load_state

MAP_FORMAT_REF = "aeoess/agent-governance-vocabulary#187@591a0bab4f5f21c546b82950713c4609fa4bdc74"
REVIEW_ACTIONS = ("factual_corrections", "survivor_classification", "review_ack")
CEILING = ("Lifecycle guidance and record export only; no property verdict, admission, endorsement, "
           "independence credit or certification.")


def _mechanical(action, command, why):
    return {"kind": "mechanical", "who": None, "action": action, "why": why, "command": command}


def _human(who, action, why):
    return {"kind": "human", "who": who, "action": action, "why": why}


def next_actions(run_dir):
    run_dir = Path(run_dir)
    scope, current = read_json(run_dir / "SCOPE.json"), load_state(run_dir)
    events = consent.load(run_dir)
    run_id, track, stage = scope["run_id"], scope.get("track", "manual"), current["state"]
    runners = scope["runner"]["maintainers"]
    items = []
    if stage == "SCOPED":
        if any(not s.get("files_sha256") for s in scope["subjects"]):
            items.append(_mechanical("pin", f"aacp run pin {run_id}", "record the SHA-256 of every pinned file"))
        elif track == "self_service":
            items.append(_mechanical("freeze", f"aacp run freeze {run_id} --not-preregistered",
                                     "freeze the plan; or freeze, publish the hash and pass --published-ref"))
        else:
            if not scope.get("agreement_ref"):
                items += [_human(r, "agreement_ref", "link the issue or comment where the scope was agreed")
                          for r in runners]
            for action, why in (("scope_agreed", "each agreement party confirms the scope; conditions may be attached"),
                                ("run_authorized", "each agreement party authorises the run")):
                done = {consent.handle(e["who"]) for e in events if e["action"] == action}
                items += [_human(p, action, why) for p in scope["agreement_parties"] if consent.handle(p) not in done]
            if not items:
                if current.get("plan_sha256") is None:
                    items.append(_mechanical("freeze", f"aacp run freeze {run_id}", "write the plan and print its hash"))
                else:
                    items += [_human(r, "publish plan hash", "publish the printed hash, then pass --published-ref")
                              for r in runners]
    elif stage == "FROZEN":
        if track == "manual" and scope["kind"] == "verification":
            admitted = consent.admissions(events)
            items += [_human(r, f"admission of {i['id']}", "decide relevance, provenance and scope before inference")
                      for i in scope["inputs"] if i["id"] not in admitted for r in runners]
        if not items:
            items.append(_mechanical("run", f"aacp run run {run_id}", "execute the frozen plan"))
    elif stage == "RUN":
        items.append(_mechanical("package", f"aacp run package {run_id}", "build the delivery package"))
    elif stage == "PACKAGED":
        items.append(_mechanical("share", f"aacp run share {run_id}", "deliver privately with read-only access"))
    elif stage in ("SHARED_PRIVATE", "REVIEWED"):
        items += _publication_items(scope, current, events)
    elif stage == "PUBLISHED":
        items.append(_mechanical("export map", f"aacp export map {run_id} --out <dir>",
                                 "write the evidence record for a map pull request (opened by a person)"))
    next_command = None if any(i["kind"] == "human" for i in items) else next(
        (i["command"] for i in items if i["kind"] == "mechanical"), None)
    for item in items:
        item.pop("command", None)
    return {"run_id": run_id, "track": track, "state": stage, "outstanding": items, "next_command": next_command}


def _publication_items(scope, current, events):
    run_id = scope["run_id"]
    since = current.get("consent_index_at_share", 0)
    if scope.get("track") == "self_service":
        terms = scope["offer_terms"]["publication"]
        maintainers = consent.handles(scope["offer_terms"]["maintainers"])
        declined = [e for e in events[since:] if e["action"] in ("publication_declined", "withdrawn")
                    and consent.handle(e["who"]) in maintainers]
        if declined and terms["unresolved_disagreement"] == "HOLD":
            return [_human(r, "withhold or resolve", "a producer maintainer declined and the offer says HOLD")
                    for r in scope["runner"]["maintainers"]]
        if terms["mode"] == "PUBLIC_AFTER_REVIEW":
            shared = datetime.strptime(current["shared_at"], "%Y-%m-%dT%H:%M:%SZ")
            opens = (shared + timedelta(days=terms["review_window_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
            return [_mechanical("publish", f"aacp run publish {run_id}",
                                f"allowed from {opens}, when the producer's review window has elapsed")]
        return [_mechanical("publish", f"aacp run publish {run_id}", "the offer allows immediate publication")]
    items = []
    if current["state"] == "SHARED_PRIVATE":
        reviewers = sorted(set(scope["publication"]["approvers"]) | {m for s in scope["subjects"] for m in s["maintainers"]})
        items += [_human(r, "review", "record factual corrections or a review addendum") for r in reviewers]
        return items
    status = consent.publication_status(events, scope["publication"]["approvers"], since=since)
    if status == "declined":
        return [_mechanical("withhold", f"aacp run withhold {run_id}", "an approver declined publication")]
    approved = {consent.handle(e["who"]) for e in events[since:] if e["action"] == "publication_approved"}
    items += [_human(a, "publication_approved", "each approver decides on publication after delivery")
              for a in scope["publication"]["approvers"] if consent.handle(a) not in approved]
    if not items:
        items.append(_mechanical("publish", f"aacp run publish {run_id}", "every approver approved after delivery"))
    return items


def _results_as_emitted(run_dir, scope):
    if scope["kind"] == "verification":
        counts = {}
        for r in read_json(run_dir / "results" / "claims.json")["records"]:
            key = r["result"] or r["execution"]
            counts[key] = counts.get(key, 0) + 1
        return counts
    return {row["id"]: read_json(run_dir / "results" / f"{row['id']}.json")["status"] for row in scope["rows"]}


def evidence_record(run_dir, include_unpublished=False):
    run_dir = Path(run_dir)
    scope, current = read_json(run_dir / "SCOPE.json"), load_state(run_dir)
    events = consent.load(run_dir)
    published = current["state"] == "PUBLISHED"
    if not published and not include_unpublished:
        raise GateError(f"{scope['run_id']} is {current['state']}, not PUBLISHED; pass --include-unpublished "
                        "to export a record without results")
    track = scope.get("track", "manual")
    reviews = [{"by": e["who"], "date": e["at"][:10], "kind": e["action"], "ref": e["ref"]}
               for e in events if e["action"] in REVIEW_ACTIONS]
    if not published:
        record_state = "private, not published"
    elif track == "self_service" and not reviews:
        record_state = "published, unreviewed"
    else:
        record_state = "published after review"
    per = independence.per_claim(scope)
    repository = current.get("repository")
    notes = [f"Track: {track}." + (f" Offer {scope['offer']['offer_id']} at {scope['offer']['repo']}@"
                                   f"{scope['offer']['commit'][:12]}." if track == "self_service" else "")]
    notes.append(f"Run label {scope['independence']} ({independence.FEDERATION[scope['independence']]}, "
                 f"{independence.BCR[scope['independence']]}).")
    if current.get("preregistered") is False:
        notes.append("Plan hash was not published before execution.")
    for c in consent.conditions(events):
        notes.append(f"Condition by {c['who']} on {', '.join(c['claims'])}: {c['text']}")
    if any(e.get("drafted_by", "human") != "human" or e.get("ai_assisted") for e in events):
        notes.append("Some recorded statements were drafted with AI assistance (see CONSENT.json).")
    if not published:
        notes.append("Results are withheld until publication.")
    record = {
        "id": scope["run_id"],
        "type": "self_service_run" if track == "self_service" else "manual_run",
        "source": f"https://github.com/{repository}/tree/{current['delivery_commit']}" if repository else "local",
        "record_state": record_state,
        "runner": ", ".join(scope["runner"]["maintainers"]),
        "runner_authored": list(scope.get("runner_authored", [])),
        "independent_for": [cid for cid, v in per.items() if v["independent"]],
        "not_independent_for": [f"{cid}: {v['reason']}" for cid, v in per.items() if not v["independent"]],
    }
    if published:
        record["results_as_emitted"] = _results_as_emitted(run_dir, scope)
    record.update({"reviews": reviews, "note": " ".join(notes), "format_ref": MAP_FORMAT_REF})
    return record


def write_evidence(run_dir, out_dir, include_unpublished=False):
    import yaml
    record = evidence_record(run_dir, include_unpublished)
    path = Path(out_dir) / "evidence" / f"{record['id']}.yaml"
    if path.exists():
        raise FileExistsError(f"{path} exists; refusing to overwrite it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path, record


def main(argv):
    """aacp next RUN [--json] | aacp export map RUN --out DIR [--include-unpublished] [--json]."""
    import argparse
    import json
    import sys

    from conformance.lab.config import load_config
    from conformance.lab.errors import LabError

    json_output = "--json" in argv
    parser = argparse.ArgumentParser(prog="aacp")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("next", help="what a lab run is waiting for")
    p.add_argument("run_id")
    p.add_argument("--json", action="store_true")
    p = commands.add_parser("export", help="export records for the federation map")
    p.add_argument("format", choices=["map"])
    p.add_argument("run_id")
    p.add_argument("--out", required=True)
    p.add_argument("--include-unpublished", action="store_true")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    run_dir = Path(load_config()["runs_dir"]) / args.run_id
    result = {"schema_version": "aacp-command-result-v1", "command": args.command, "status": "OK",
              "verification_status": "NOT_RUN", "property_verdict": None, "data": {}, "errors": [],
              "next_action": {"action": "none", "command": None, "output_schema": "aacp-command-result-v1"},
              "claim_ceiling": CEILING}
    code = 0
    try:
        if args.command == "next":
            data = next_actions(run_dir)
            result["data"] = data
            first = next((i for i in data["outstanding"]), None)
            result["next_action"] = {"action": first["action"] if first else "none",
                                     "command": data["next_command"], "output_schema": "aacp-command-result-v1"}
        else:
            path, record = write_evidence(run_dir, args.out, args.include_unpublished)
            result["data"] = {"written": str(path), "record": record}
            result["next_action"] = {"action": "open_map_pull_request_as_a_person", "command": None,
                                     "output_schema": "aacp-command-result-v1"}
    except FileExistsError as error:
        result.update(status="INVALID_INPUT", errors=[{"code": "ALREADY_EXISTS", "message": str(error)}])
        code = 2
    except (LabError, FileNotFoundError) as error:
        result.update(status="INVALID_INPUT", errors=[{"code": "INVALID_RUN", "message": str(error)}])
        code = 2
    except OSError as error:
        result.update(status="ERROR", errors=[{"code": "LOCAL_IO_ERROR", "message": str(error)}])
        code = 3
    if json_output:
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    else:
        for error in result["errors"]:
            print(f"{error['code']}: {error['message']}", file=sys.stderr)
        if args.command == "next" and result["data"]:
            data = result["data"]
            print(f"{data['run_id']}: {data['state']} ({data['track']})")
            for item in data["outstanding"]:
                who = f"{item['who']}: " if item["who"] else ""
                print(f"- [{item['kind']}] {who}{item['action']} ({item['why']})")
            print(f"Next: {data['next_command'] or 'waiting for the people named above'}")
        elif result["data"]:
            print(f"wrote {result['data']['written']}; a person opens any map pull request")
    return code
