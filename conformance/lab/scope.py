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
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHECK = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$")
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
        if require_pins and not isinstance(scope.get("offer_terms"), dict):
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
    elif kind == "verification":
        p.extend(_verification_problems(scope))
    if p:
        raise ScopeError("; ".join(p))
    return scope


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
    if len(scope.get("subjects") or []) != 1:
        p.append("self_service runs measure exactly one subject, the offer's")
    if "publication" in scope:
        p.append("self_service publication is runner-attributed or taken from the producer offer; remove publication")
    if not _text(scope.get("procedure")):
        p.append("self_service needs procedure: the offered procedure id")
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
