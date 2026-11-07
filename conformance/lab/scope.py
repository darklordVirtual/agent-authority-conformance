"""SCOPE.json structural validation (RUN-PROTOCOL-v0.3 §5).

Standard library only, because the lab is vendored into every run package.
schema/lab/scope.schema.json documents the same structure; a repository test
checks that both agree on the committed fixtures.
"""

import re
from pathlib import Path, PurePosixPath

from .canonical import find_forbidden_keys, read_json
from .errors import ScopeError

KINDS = ("adequacy", "verification")
TRACKS = ("manual", "self_service")
INDEPENDENCE = ("SELF_RUN", "REPRODUCTION", "SECOND_IMPLEMENTATION", "INDEPENDENT_IMPLEMENTATION")
ENGINES = ("native", "corpus_adequacy")
# How a verification input reaches a check: parsed JSON, or the exact bytes (needed
# whenever a check verifies a signature or a digest over the bytes as published).
INPUT_FORMATS = ("json", "bytes")
# Probes are runner-authored observations about a pinned artifact, separate from
# claim results. The class says what kind of property was probed; it is not a verdict.
PROBE_CLASSES = ("SPEC_IMPLEMENTATION_DIVERGENCE", "CONSTRUCTION_AMBIGUITY", "BINDING_GAP", "FRAMING_GAP",
                 "KEY_REUSE", "TRUST_ANCHOR", "ATTESTATION_SCOPE", "TERMINOLOGY_CHANGE",
                 "PROVENANCE_ATTRIBUTION", "OTHER")
# The runner's own judgment of a probe's practical weight. Never summed or ranked.
ASSESSMENT_LEVELS = ("informational", "low", "medium", "high")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHECK = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$")
LINES = re.compile(r"^[1-9][0-9]*(-[1-9][0-9]*)?$")
ID = re.compile(r"^[A-Za-z0-9._-]+$")
FILE = "SCOPE.json"


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _texts(value):
    return isinstance(value, list) and len(value) > 0 and all(_text(v) for v in value)


def _relative(path):
    pure = PurePosixPath(path)
    return not pure.is_absolute() and ".." not in pure.parts


def track(scope):
    """No track means manual: every run written before tracks existed stays manual."""
    return scope.get("track", "manual")


def _ceiling_ok(ceiling):
    return isinstance(ceiling, dict) and _texts(ceiling.get("establishes")) and _texts(ceiling.get("does_not_establish"))


def validate_scope(scope, *, require_pins=False):
    if not isinstance(scope, dict):
        raise ScopeError("SCOPE.json must be an object")
    p = [f"aggregate key {k} is not allowed" for k in find_forbidden_keys(scope)]
    if scope.get("lab_version") != "0.3":
        p.append("lab_version must be '0.3'")
    if not _text(scope.get("run_id")) or not re.fullmatch(r"[A-Za-z0-9._-]+", scope["run_id"]):
        p.append("run_id must be letters, digits, '.', '_' or '-'")
    kind = scope.get("kind")
    if kind not in KINDS:
        p.append(f"kind must be one of {', '.join(KINDS)}")
    independence = scope.get("independence")
    if independence not in INDEPENDENCE:
        p.append(f"independence must be one of {', '.join(INDEPENDENCE)}")
    if independence == "INDEPENDENT_IMPLEMENTATION" and not _text(scope.get("independence_statement")):
        p.append("INDEPENDENT_IMPLEMENTATION requires independence_statement")
    if "procedure" in scope and not _text(scope["procedure"]):
        p.append("procedure must be a nonempty string when present")
    for key in ("verifier_authors", "trust_material"):
        if key in scope and not _texts(scope[key]):
            p.append(f"{key} must be a nonempty list of strings when present")
    authored = scope.get("runner_authored")
    if authored is not None and not (isinstance(authored, list) and all(_text(a) for a in authored)):
        p.append("runner_authored must be a list of nonempty strings")
    for item in scope.get("claims", []) + scope.get("rows", []) if isinstance(
            scope.get("claims", []), list) and isinstance(scope.get("rows", []), list) else []:
        if not isinstance(item, dict) or "independent" not in item:
            continue
        w = f"claim or row {item.get('id')!r}"
        if not isinstance(item["independent"], bool):
            p.append(f"{w}: independent must be true or false")
        elif item["independent"] is False and not _text(item.get("not_independent_reason")):
            p.append(f"{w}: independent false requires not_independent_reason")
        elif item["independent"] is True and independence != "INDEPENDENT_IMPLEMENTATION":
            p.append(f"{w}: a claim cannot be more independent than the run label {independence}")
    selected = track(scope)
    if selected not in TRACKS:
        p.append(f"track must be one of {', '.join(TRACKS)}")
    ref = scope.get("agreement_ref")
    if ref is not None and not (isinstance(ref, str) and ref.startswith("https://")):
        p.append("agreement_ref must be null or an https URL")
    runner = scope.get("runner")
    if not (isinstance(runner, dict) and _text(runner.get("project")) and _texts(runner.get("maintainers"))):
        p.append("runner needs project and maintainers")
    if selected == "self_service":
        p.extend(_self_service_problems(scope))
        if require_pins and "offer" in scope and not isinstance(scope.get("offer_terms"), dict):
            p.append("offer_terms is missing; run pin to read the offer")
    elif not _texts(scope.get("agreement_parties")):
        p.append("agreement_parties must be a nonempty list of handles")
    subjects = scope.get("subjects")
    if not (isinstance(subjects, list) and subjects):
        p.append("subjects must be a nonempty list")
    else:
        for i, subject in enumerate(subjects):
            p.extend(_subject_problems(i, subject, require_pins))
    ceiling = scope.get("claim_ceiling")
    ceiling = ceiling if isinstance(ceiling, dict) else {}
    for key in ("establishes", "does_not_establish"):
        if not _texts(ceiling.get(key)):
            p.append(f"claim_ceiling.{key} must be a nonempty list")
    if selected != "self_service":
        pub = scope.get("publication")
        pub = pub if isinstance(pub, dict) else {}
        if pub.get("private_first") is not True:
            p.append("publication.private_first must be true")
        if pub.get("unreleased_citable") is not False:
            p.append("publication.unreleased_citable must be false")
        if not _texts(pub.get("approvers")):
            p.append("publication.approvers must be a nonempty list of handles")
    if kind == "adequacy":
        p.extend(_adequacy_problems(scope))
        if "probes" in scope:
            p.append("probes are only for verification runs")
    elif kind == "verification":
        p.extend(_verification_problems(scope))
        p.extend(_probe_problems(scope, require_pins))
    if "challenge" in scope:
        p.extend(_challenge_problems(scope["challenge"]))
    if p:
        raise ScopeError("; ".join(p))
    return scope


def _challenge_problems(challenge):
    """A public request to verify something. Context only: it is never consent, an offer,
    admission or a publication approval, and answering it is not endorsement."""
    if not isinstance(challenge, dict):
        return ["challenge must be an object"]
    p = []
    if not (isinstance(challenge.get("ref"), str) and challenge["ref"].startswith("https://")):
        p.append("challenge.ref must be an https URL to the public statement")
    if not _text(challenge.get("by")):
        p.append("challenge.by must name who made the challenge")
    if not _texts(challenge.get("asked")):
        p.append("challenge.asked must list what the challenge asked, in the runner's words")
    if not isinstance(challenge.get("requests_endorsement"), bool):
        p.append("challenge.requests_endorsement must be true or false")
    extra = sorted(set(challenge) - {"ref", "by", "asked", "requests_endorsement"})
    if extra:
        p.append(f"challenge has unknown key(s): {', '.join(extra)}")
    return p


def _probe_problems(scope, require_pins):
    probes = scope.get("probes")
    if probes is None:
        return []
    if not (isinstance(probes, list) and probes):
        return ["probes must be a nonempty list when present"]
    p = []
    inputs = {i.get("id") for i in scope.get("inputs") or [] if isinstance(i, dict)}
    claim_ids = {c.get("id") for c in scope.get("claims") or [] if isinstance(c, dict)}
    subjects = scope.get("subjects") if isinstance(scope.get("subjects"), list) else []
    seen = set()
    for i, probe in enumerate(probes):
        w = f"probes[{i}]"
        if not isinstance(probe, dict):
            p.append(f"{w} must be an object")
            continue
        pid = probe.get("id")
        if not (_text(pid) and ID.fullmatch(pid)):
            p.append(f"{w}.id must be letters, digits, '.', '_' or '-'")
        elif pid in seen or pid in claim_ids:
            p.append(f"{w}.id {pid!r} is not unique among claims and probes")
        seen.add(pid)
        if not _text(probe.get("text")):
            p.append(f"{w}.text is required: the property probed, stated neutrally")
        if probe.get("class") not in PROBE_CLASSES:
            p.append(f"{w}.class must be one of {', '.join(PROBE_CLASSES)}")
        if not (isinstance(probe.get("check"), str) and CHECK.match(probe["check"])):
            p.append(f"{w}.check must be <module>:<function> in verifier/")
        if not _texts(probe.get("reads_fields")):
            p.append(f"{w}.reads_fields must be a nonempty list")
        if not (_texts(probe.get("inputs")) and set(probe["inputs"]) <= inputs):
            p.append(f"{w}.inputs must name declared inputs")
        elif len(set(probe["inputs"])) != len(probe["inputs"]):
            p.append(f"{w}.inputs must be unique")
        assessment = probe.get("runner_assessment")
        if not (isinstance(assessment, dict) and assessment.get("level") in ASSESSMENT_LEVELS
                and _text(assessment.get("rationale")) and set(assessment) == {"level", "rationale"}):
            p.append(f"{w}.runner_assessment needs level ({', '.join(ASSESSMENT_LEVELS)}) and rationale")
        if "remediation" in probe and not _text(probe["remediation"]):
            p.append(f"{w}.remediation must be a nonempty string when present")
        locators = probe.get("source_locators", [])
        if not isinstance(locators, list):
            p.append(f"{w}.source_locators must be a list")
            continue
        for j, loc in enumerate(locators):
            lw = f"{w}.source_locators[{j}]"
            if not (isinstance(loc, dict) and isinstance(loc.get("subject"), int)
                    and not isinstance(loc.get("subject"), bool) and 0 <= loc["subject"] < len(subjects)):
                p.append(f"{lw} needs a valid subject index")
                continue
            if not (_text(loc.get("path")) and _relative(loc["path"])):
                p.append(f"{lw}.path must be relative")
                continue
            if not (isinstance(loc.get("lines"), str) and LINES.fullmatch(loc["lines"])):
                p.append(f"{lw}.lines must be N or N-M")
            elif "-" in loc["lines"] and int(loc["lines"].split("-")[0]) > int(loc["lines"].split("-")[1]):
                p.append(f"{lw}.lines range is reversed")
            if not _text(loc.get("note")):
                p.append(f"{lw}.note is required")
            pinned = subjects[loc["subject"]].get("files_sha256") if isinstance(subjects[loc["subject"]], dict) else None
            if require_pins and isinstance(pinned, dict) and loc["path"] not in pinned:
                p.append(f"{lw}.path {loc['path']} is not a pinned file of subject {loc['subject']}")
    return p


def _self_service_problems(scope):
    p = []
    has_offer = "offer" in scope
    has_public = "public_boundary" in scope
    if has_offer == has_public:
        p.append("self_service needs exactly one basis: offer or public_boundary")
    elif has_offer:
        from .offer import validate_ref
        try:
            validate_ref(scope.get("offer"))
        except ScopeError as exc:
            p.append(f"invalid self_service offer: {exc}")
    else:
        from .public_boundary import validate_ref
        try:
            validate_ref(scope.get("public_boundary"))
        except ScopeError as exc:
            p.append(f"invalid public_boundary: {exc}")
    if scope.get("kind") != "verification":
        p.append("self_service allows only kind verification; adequacy and mutation need the manual track")
    subjects = scope.get("subjects") or []
    if has_offer and len(subjects) != 1:
        p.append("self_service runs measure exactly one subject, the offer's")
    elif has_public and not has_offer:
        p.extend(boundary_binding_problems(scope.get("public_boundary"), subjects))
    if "publication" in scope:
        p.append("self_service publication is runner-attributed or taken from the producer offer; remove publication")
    if not _text(scope.get("procedure")):
        p.append("self_service needs procedure: the offered procedure id")
    return p


def _repo_key(url):
    return str(url or "").rstrip("/").removesuffix(".git").lower()


def boundary_binding_problems(boundary, subjects):
    """A public boundary vouches only for bytes of its own repository: every subject is a
    revision of that repository, and subject 0 (the primary subject) is pinned at exactly
    the boundary commit, so the boundary text describes the bytes that are verified. Other
    subjects are earlier or later revisions kept for comparison."""
    if not isinstance(boundary, dict):
        return []  # validate_ref reports the malformed boundary
    if not subjects:
        return ["a public_boundary run needs a primary subject"]
    p = []
    repo = _repo_key(boundary.get("repo"))
    foreign = [i for i, s in enumerate(subjects) if not isinstance(s, dict) or _repo_key(s.get("repo")) != repo]
    if foreign:
        p.append("public_boundary covers only its own repository; subject(s) "
                 f"{', '.join(map(str, foreign))} point elsewhere")
    primary = subjects[0] if isinstance(subjects[0], dict) else {}
    if primary.get("commit") != boundary.get("commit"):
        p.append("subjects[0] is the primary subject and must be pinned at the public_boundary commit")
    return p



def _subject_problems(i, s, require_pins):
    w = f"subjects[{i}]"
    if not isinstance(s, dict):
        return [f"{w} must be an object"]
    p = [f"{w}.{key} is required" for key in ("project", "repo", "license", "attribution")
         if not _text(s.get(key))]
    if _text(s.get("repo")) and not s["repo"].startswith("https://"):
        p.append(f"{w}.repo must be an https URL")
    if not _texts(s.get("maintainers")):
        p.append(f"{w}.maintainers must be a nonempty list")
    if not (isinstance(s.get("commit"), str) and COMMIT.match(s["commit"])):
        p.append(f"{w}.commit must be a full 40-character lowercase hex commit")
    if not _texts(s.get("paths")):
        p.append(f"{w}.paths must be a nonempty list")
    else:
        p.extend(f"{w}.paths entry {path!r} must be relative" for path in s["paths"] if not _relative(path))
    files = s.get("files_sha256")
    if not (isinstance(files, dict) and all(_relative(k) and isinstance(v, str) and SHA256.match(v)
                                            for k, v in files.items())):
        p.append(f"{w}.files_sha256 must map relative paths to sha256 hex")
    elif require_pins and not files:
        p.append(f"{w}.files_sha256 is empty; run pin first")
    return p


def _adequacy_problems(scope):
    p = []
    if len(scope.get("subjects") or []) != 1:
        p.append("adequacy runs measure exactly one subject")
    rows = scope.get("rows")
    if not (isinstance(rows, list) and rows):
        return p + ["rows must be a nonempty list"]
    ids = [r.get("id") for r in rows if isinstance(r, dict)]
    if len(ids) != len(rows) or len(set(ids)) != len(ids):
        p.append("row ids must be unique")
    for i, row in enumerate(rows):
        w = f"rows[{i}]"
        if not isinstance(row, dict):
            p.append(f"{w} must be an object")
            continue
        if not (_text(row.get("id")) and re.fullmatch(r"[A-Za-z0-9._-]+", row["id"])):
            p.append(f"{w}.id must be letters, digits, '.', '_' or '-'")
        command = row.get("command")
        if not (_texts(command) and any("{case}" in part for part in command)):
            p.append(f"{w}.command must be a list containing {{case}}")
        if not _texts(row.get("projection")):
            p.append(f"{w}.projection must be a nonempty list")
        if not _texts(row.get("fault_sets")):
            p.append(f"{w}.fault_sets must be a nonempty list")
        if not _texts(row.get("cases")):
            p.append(f"{w}.cases must be a nonempty list of case ids")
        elif len(set(row["cases"])) != len(row["cases"]):
            p.append(f"{w}.cases must be unique")
        expected = row.get("expected_from")
        if expected is not None and not (isinstance(expected, dict) and all(
                _text(expected.get(k)) for k in ("path", "list_key", "id_key", "field"))
                and _relative(expected["path"])):
            p.append(f"{w}.expected_from needs a relative path, list_key, id_key and field")
    controls = scope.get("controls")
    controls = controls if isinstance(controls, dict) else {}
    for key in ("positive", "inert"):
        if not _text(controls.get(key)):
            p.append(f"controls.{key} is required")
    engine = scope.get("engine")
    engine = engine if isinstance(engine, dict) else {}
    if engine.get("name") not in ENGINES:
        p.append(f"engine.name must be one of {', '.join(ENGINES)}")
    if engine.get("cross_check") not in (None, *ENGINES) or (
            engine.get("cross_check") is not None and engine.get("cross_check") == engine.get("name")):
        p.append("engine.cross_check must be null or the other engine")
    return p


def _verification_problems(scope):
    p = []
    inputs = scope.get("inputs")
    if not (isinstance(inputs, list) and inputs):
        return ["inputs must be a nonempty list"]
    count = len(scope.get("subjects") or [])
    ids = set()
    for i, item in enumerate(inputs):
        if not (isinstance(item, dict) and _text(item.get("id")) and _text(item.get("path"))
                and _relative(item["path"]) and isinstance(item.get("subject"), int)
                and not isinstance(item.get("subject"), bool) and 0 <= item["subject"] < count):
            p.append(f"inputs[{i}] needs id, a relative path and a valid subject index")
            continue
        if item.get("format", "json") not in INPUT_FORMATS:
            p.append(f"inputs[{i}].format must be one of {', '.join(INPUT_FORMATS)}")
        if item["id"] in ids:
            p.append(f"inputs[{i}].id {item['id']!r} is duplicated")
        ids.add(item["id"])
    claims = scope.get("claims")
    if not (isinstance(claims, list) and claims):
        return p + ["claims must be a nonempty list"]
    claim_ids = set()
    for i, claim in enumerate(claims):
        w = f"claims[{i}]"
        if not isinstance(claim, dict):
            p.append(f"{w} must be an object")
            continue
        for key in ("id", "text", "layer"):
            if not _text(claim.get(key)):
                p.append(f"{w}.{key} is required")
        if claim.get("id") in claim_ids:
            p.append(f"{w}.id is duplicated")
        claim_ids.add(claim.get("id"))
        if not (isinstance(claim.get("check"), str) and CHECK.match(claim["check"])):
            p.append(f"{w}.check must be <module>:<function> in verifier/")
        if not _texts(claim.get("reads_fields")):
            p.append(f"{w}.reads_fields must be a nonempty list")
        if not (_texts(claim.get("inputs")) and set(claim["inputs"]) <= ids):
            p.append(f"{w}.inputs must name declared inputs")
        controls = claim.get("negative_controls")
        if controls is not None and not (_texts(controls) and set(controls) <= set(claim.get("inputs") or [])):
            p.append(f"{w}.negative_controls must name inputs of this claim")
        if "claim_ceiling" in claim and not _ceiling_ok(claim["claim_ceiling"]):
            p.append(f"{w}.claim_ceiling needs nonempty establishes and does_not_establish")
        if claim.get("temporal") is True and not _text(scope.get("reference_time")):
            p.append(f"{w} is temporal; reference_time is required")
    return p


def load_scope(run_dir, *, require_pins=False):
    return validate_scope(read_json(Path(run_dir) / FILE), require_pins=require_pins)
