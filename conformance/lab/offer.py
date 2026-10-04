"""Open verification offers: a producer's standing consent for self-service runs.

The producer commits `aacp-offers.json` in its own repository. One offer covers
one frozen subject commit and names the inputs it pre-admits, the claims it opens
with their ceilings, and the publication policy it accepts. The runner pins the
offer file by commit and SHA-256. Before freeze, run and publish the lab re-reads
the producer's default branch: a missing, revoked or expired offer refuses new
work. Nothing already published is changed (nothing is retroactive).

Standard library only, because the lab is vendored into every package.
"""

import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path, PurePosixPath

from .canonical import find_forbidden_keys, read_json, sha256_file
from .errors import GateError, PinError, ScopeError
from .pins import fetch

SCHEMA_VERSION = "aacp-offers-v1"
MODES = ("PUBLIC_IMMEDIATE", "PUBLIC_AFTER_REVIEW")
DISAGREEMENT = ("PUBLISH_WITH_DISAGREEMENT", "HOLD")
KINDS = ("verification",)
ID = re.compile(r"^[A-Za-z0-9._-]+$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _texts(value):
    return isinstance(value, list) and len(value) > 0 and all(_text(v) for v in value)


def _relative(path):
    pure = PurePosixPath(path)
    return _text(path) and not pure.is_absolute() and ".." not in pure.parts


def _date(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) and len(value) == 10 else None
    except ValueError:
        return None


def _entry_problems(i, e):
    w = f"offers[{i}]"
    if not isinstance(e, dict):
        return [f"{w} must be an object"]
    p = []
    if not (isinstance(e.get("offer_id"), str) and ID.match(e["offer_id"])):
        p.append(f"{w}.offer_id must be letters, digits, '.', '_' or '-'")
    if not isinstance(e.get("revoked"), bool):
        p.append(f"{w}.revoked must be true or false")
    if _date(e.get("expires")) is None:
        p.append(f"{w}.expires must be a YYYY-MM-DD date")
    producer = e.get("producer") if isinstance(e.get("producer"), dict) else {}
    if not (_text(producer.get("project")) and _texts(producer.get("maintainers"))):
        p.append(f"{w}.producer needs project and maintainers")
    subject = e.get("subject") if isinstance(e.get("subject"), dict) else {}
    if not (_text(subject.get("repo")) and subject["repo"].startswith("https://")):
        p.append(f"{w}.subject.repo must be an https URL")
    if not (isinstance(subject.get("commit"), str) and COMMIT.match(subject["commit"])):
        p.append(f"{w}.subject.commit must be a full 40-character lowercase hex commit")
    if not (_texts(subject.get("paths")) and all(_relative(x) for x in subject["paths"])):
        p.append(f"{w}.subject.paths must be a nonempty list of relative paths")
    inputs = e.get("inputs")
    if not (isinstance(inputs, list) and inputs and all(
            isinstance(x, dict) and _text(x.get("id")) and _relative(x.get("path")) for x in inputs)):
        p.append(f"{w}.inputs must be a nonempty list of {{id, relative path}}")
    elif len({x["id"] for x in inputs}) != len(inputs):
        p.append(f"{w}.inputs ids must be unique")
    claims = e.get("claims")
    if not (isinstance(claims, list) and claims):
        p.append(f"{w}.claims must be a nonempty list")
    else:
        for j, c in enumerate(claims):
            ceiling = c.get("claim_ceiling") if isinstance(c, dict) else None
            if not (isinstance(c, dict) and _text(c.get("id")) and _text(c.get("text"))
                    and isinstance(ceiling, dict) and _texts(ceiling.get("establishes"))
                    and _texts(ceiling.get("does_not_establish"))):
                p.append(f"{w}.claims[{j}] needs id, text and claim_ceiling with establishes and does_not_establish")
        ids = [c.get("id") for c in claims if isinstance(c, dict)]
        if len(set(ids)) != len(ids):
            p.append(f"{w}.claims ids must be unique")
    kinds = e.get("kinds")
    if not (_texts(kinds) and set(kinds) <= set(KINDS)):
        p.append(f"{w}.kinds may contain only {', '.join(KINDS)}; adequacy and mutation need the manual track")
    if e.get("executes_producer_code") is not False:
        p.append(f"{w}.executes_producer_code must be false; running producer code needs the manual track")
    pub = e.get("publication") if isinstance(e.get("publication"), dict) else {}
    if pub.get("mode") not in MODES:
        p.append(f"{w}.publication.mode must be one of {', '.join(MODES)}")
    window = pub.get("review_window_days")
    if pub.get("mode") == "PUBLIC_AFTER_REVIEW":
        if not (isinstance(window, int) and not isinstance(window, bool) and window >= 1):
            p.append(f"{w}.publication.review_window_days must be a whole number of days >= 1")
    elif window is not None:
        p.append(f"{w}.publication.review_window_days must be null for {pub.get('mode')}")
    if pub.get("unresolved_disagreement") not in DISAGREEMENT:
        p.append(f"{w}.publication.unresolved_disagreement must be one of {', '.join(DISAGREEMENT)}")
    return p


def validate_offers(doc):
    if not isinstance(doc, dict):
        raise ScopeError("offers file must be a JSON object")
    p = [f"aggregate key {k} is not allowed" for k in find_forbidden_keys(doc)]
    if doc.get("schema_version") != SCHEMA_VERSION:
        p.append(f"schema_version must be {SCHEMA_VERSION!r}")
    offers = doc.get("offers")
    if not (isinstance(offers, list) and offers):
        p.append("offers must be a nonempty list")
    else:
        for i, entry in enumerate(offers):
            p.extend(_entry_problems(i, entry))
        ids = [e.get("offer_id") for e in offers if isinstance(e, dict)]
        dupes = sorted({x for x in ids if ids.count(x) > 1})
        if dupes:
            p.append(f"duplicate offer_id {', '.join(map(str, dupes))}: an offer must be unambiguous")
    if p:
        raise ScopeError("; ".join(p))
    return doc


def find(doc, offer_id):
    for entry in doc["offers"]:
        if entry["offer_id"] == offer_id:
            return entry
    raise ScopeError(f"offer {offer_id!r} is not in the offers file")


def validate_ref(ref):
    if not (isinstance(ref, dict) and _text(ref.get("repo")) and ref["repo"].startswith("https://")
            and isinstance(ref.get("commit"), str) and COMMIT.match(ref["commit"])
            and _relative(ref.get("path")) and isinstance(ref.get("offer_id"), str) and ID.match(ref["offer_id"])
            and isinstance(ref.get("sha256"), str) and SHA256.match(ref["sha256"])):
        raise ScopeError("offer must be {repo (https), commit (40 hex), path (relative), offer_id, sha256}")
    return ref


def fetch_pinned(ref, workdir=None):
    """The offer entry exactly as pinned: the file at that commit with that SHA-256."""
    validate_ref(ref)
    with tempfile.TemporaryDirectory(prefix="aac-offer-", dir=workdir) as tmp:
        clone = fetch(ref["repo"], ref["commit"], Path(tmp) / "offer")
        path = clone / ref["path"]
        if not path.is_file():
            raise PinError(f"{ref['path']} does not exist at offer commit {ref['commit']}")
        if sha256_file(path) != ref["sha256"]:
            raise PinError(f"{ref['path']} at {ref['commit']} does not have the pinned sha256")
        return find(validate_offers(read_json(path)), ref["offer_id"])


def check_tip(ref, now, workdir=None):
    """Refuse new work when the producer's default branch withdrew, revoked or let the offer expire."""
    validate_ref(ref)
    with tempfile.TemporaryDirectory(prefix="aac-offer-tip-", dir=workdir) as tmp:
        dest = Path(tmp) / "tip"
        result = subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--", ref["repo"], str(dest)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise PinError(f"cannot read the producer's default branch: {result.stderr.strip()}")
        path = dest / ref["path"]
        if not path.is_file():
            raise GateError(f"offer withdrawn: {ref['path']} is gone from the producer's default branch")
        doc = validate_offers(read_json(path))
    entry = next((e for e in doc["offers"] if e["offer_id"] == ref["offer_id"]), None)
    if entry is None:
        raise GateError(f"offer withdrawn: the default branch no longer lists {ref['offer_id']}")
    if entry["revoked"]:
        raise GateError(f"offer {ref['offer_id']} was revoked by the producer")
    if date.fromisoformat(entry["expires"]) < date.fromisoformat(now[:10]):
        raise GateError(f"offer {ref['offer_id']} expired on {entry['expires']}")
    return entry


def check_scope_against(scope, entry):
    """The scope may use only what the offer opens, exactly as the offer states it."""
    p = []
    subjects = scope.get("subjects") or []
    s = subjects[0] if len(subjects) == 1 else {}
    if len(subjects) != 1 or s.get("repo") != entry["subject"]["repo"] or s.get("commit") != entry["subject"]["commit"] \
            or sorted(s.get("paths") or []) != sorted(entry["subject"]["paths"]):
        p.append("subject must be exactly the offer's subject (repo, commit and paths)")
    if scope.get("kind") not in entry["kinds"]:
        p.append(f"kind {scope.get('kind')!r} is not offered ({', '.join(entry['kinds'])})")
    offered_inputs = {i["id"]: i["path"] for i in entry["inputs"]}
    for item in scope.get("inputs", []):
        if offered_inputs.get(item.get("id")) != item.get("path") or item.get("subject") != 0:
            p.append(f"input {item.get('id')!r} is not offered with path {item.get('path')!r}")
    offered_claims = {c["id"]: c for c in entry["claims"]}
    for claim in scope.get("claims", []):
        cid = claim.get("id")
        if cid not in offered_claims:
            p.append(f"claim {cid!r} is not offered")
        elif claim.get("claim_ceiling") != offered_claims[cid]["claim_ceiling"]:
            p.append(f"claim {cid!r} must carry the offer's claim_ceiling unchanged")
    if p:
        raise ScopeError("scope exceeds the offer: " + "; ".join(p))
