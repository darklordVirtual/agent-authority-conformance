"""Runner checks for the NTI witness package (Neutral Trust Infrastructure).

Written for AACP run protocol v0.3. Standard library only, so a package rerun needs
nothing installed. Ed25519 is RFC 8032 section 5.1.7 verification implemented here,
independent of OpenSSL and of pyca/cryptography. Subject files arrive as bytes and are
only read: no subject code is imported or executed, and no subject command is run.

Claims check what the published README says the package proves. Probes record
properties the runner observed, each with a witness anyone can recompute.
"""

import base64
import hashlib
import json
import re

# --- Ed25519 (RFC 8032) -------------------------------------------------------------

_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)
_SPKI_ED25519 = bytes.fromhex("302a300506032b6570032100")


def _inv(x):
    return pow(x, _P - 2, _P)


def _add(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    k = (y1 - x1) * (y2 - x2) % _P
    m = (y1 + x1) * (y2 + x2) % _P
    c = 2 * t1 * t2 * _D % _P
    dd = 2 * z1 * z2 % _P
    e, f, g, h = m - k, dd - c, dd + c, m + k
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(s, point):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _add(q, point)
        point = _add(point, point)
        s >>= 1
    return q


def _equal(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _recover_x(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P:
        return None
    return _P - x if (x & 1) != sign else x


def _decompress(data):
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _compress(point):
    zinv = _inv(point[2])
    x, y = point[0] * zinv % _P, point[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


_GY = 4 * _inv(5) % _P
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def ed25519_verify(public, message, signature):
    """RFC 8032 5.1.7, with the canonical-S check (S < L) that rejects malleated signatures."""
    if len(public) != 32 or len(signature) != 64:
        return False
    a = _decompress(public)
    r = _decompress(signature[:32])
    if a is None or r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), "little") % _L
    return _equal(_mul(s, _G), _add(r, _mul(h, a)))


def ed25519_sign(secret, message):
    """RFC 8032 5.1.6. Used only by tests to build synthetic packages."""
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little") & ((1 << 254) - 8) | (1 << 254)
    public = _compress(_mul(a, _G))
    r = int.from_bytes(hashlib.sha512(h[32:] + message).digest(), "little") % _L
    rs = _compress(_mul(r, _G))
    k = int.from_bytes(hashlib.sha512(rs + public + message).digest(), "little") % _L
    return rs + int.to_bytes((r + k * a) % _L, 32, "little")


def ed25519_public(secret):
    h = hashlib.sha512(secret).digest()
    return _compress(_mul(int.from_bytes(h[:32], "little") & ((1 << 254) - 8) | (1 << 254), _G))


def public_key_from_pem(pem):
    """Raw 32-byte key from an Ed25519 SubjectPublicKeyInfo PEM; None if it is not one."""
    text = pem.decode("ascii", errors="strict")
    body = re.search(r"-----BEGIN PUBLIC KEY-----(.*?)-----END PUBLIC KEY-----", text, re.S)
    if not body:
        return None
    der = base64.b64decode("".join(body.group(1).split()), validate=True)
    if len(der) != 44 or not der.startswith(_SPKI_ED25519):
        return None
    return der[len(_SPKI_ED25519):]


def pem_for(public):
    der = _SPKI_ED25519 + public
    return b"-----BEGIN PUBLIC KEY-----\n" + base64.b64encode(der) + b"\n-----END PUBLIC KEY-----\n"


# --- S5 Merkle constructions --------------------------------------------------------

LEAF = b"nti-s5-leaf-v1:"
NODE = b"nti-s5-node-v1:"


def _sha(data):
    return hashlib.sha256(data).digest()


def merkle_documented(digests):
    """README: RFC-6962-style with domain separation; an odd node is promoted unchanged.
    Bottom-up promotion gives the same root as the RFC 6962 MTH split for every count."""
    level = [_sha(LEAF + d) for d in digests]
    levels = [level]
    while len(level) > 1:
        level = [_sha(NODE + level[i] + level[i + 1]) if i + 1 < len(level) else level[i]
                 for i in range(0, len(level), 2)]
        levels.append(level)
    return level[0], levels


def merkle_rfc6962(digests):
    """RFC 6962 section 2.1 MTH with NTI's prefixes in place of 0x00 and 0x01."""
    if len(digests) == 1:
        return _sha(LEAF + digests[0])
    k = 1
    while k * 2 < len(digests):
        k *= 2
    return _sha(NODE + merkle_rfc6962(digests[:k]) + merkle_rfc6962(digests[k:]))


def merkle_duplicating(digests):
    """The rule found in the published generator and verifier: an odd last node is
    paired with itself."""
    level = [_sha(LEAF + d) for d in digests]
    levels = [level]
    while len(level) > 1:
        level = [_sha(NODE + level[i] + (level[i + 1] if i + 1 < len(level) else level[i]))
                 for i in range(0, len(level), 2)]
        levels.append(level)
    return level[0], levels


def probe_leaves(n):
    """Deterministic synthetic leaf digests: sha256(b"nti-probe-leaf-<i>") for i = 1..n."""
    return [_sha(f"nti-probe-leaf-{i}".encode()) for i in range(1, n + 1)]


# --- shared helpers -----------------------------------------------------------------

SIGNED = ("RESULTS.json", "MANIFEST.json", "SIGNATURE.sig", "PUBLIC_KEY.pem")


def _package(bundle, prefix=""):
    """The four signed-package files from a bundle, or None if any is missing."""
    try:
        return {name: bundle[prefix + name] for name in SIGNED}
    except KeyError:
        return None


def _json(data):
    return json.loads(data.decode("utf-8"))


def _flip_last(data):
    return data[:-1] + bytes([data[-1] ^ 0x01])


def _invalid(message):
    return {"execution": "INVALID_INPUT", "message": message}


def _line_of(data, needle):
    """1-based line number of the first line containing needle, or None."""
    for n, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), start=1):
        if needle in line:
            return n
    return None


def _normalised(data):
    return " ".join(data.decode("utf-8", errors="replace").split())


# --- claims (one record per input) --------------------------------------------------

def package_signature(doc, context):
    pkg = _package(doc)
    if pkg is None:
        return _invalid("bundle lacks RESULTS.json, MANIFEST.json, SIGNATURE.sig or PUBLIC_KEY.pem")
    public = public_key_from_pem(pkg["PUBLIC_KEY.pem"])
    if public is None:
        return _invalid("PUBLIC_KEY.pem is not an Ed25519 SubjectPublicKeyInfo key")
    reads = list(SIGNED)
    message = pkg["RESULTS.json"] + pkg["MANIFEST.json"]
    if not ed25519_verify(public, message, pkg["SIGNATURE.sig"]):
        return {"result": "CONTRADICTED", "reads": reads}
    discriminates = (not ed25519_verify(public, _flip_last(message), pkg["SIGNATURE.sig"])
                     and not ed25519_verify(public, pkg["MANIFEST.json"] + pkg["RESULTS.json"], pkg["SIGNATURE.sig"]))
    if not discriminates:
        return {"result": "NOT_ESTABLISHED", "reads": reads,
                "unresolved_obligations": ["verification did not fail on a one-byte change or on reversed order"]}
    return {"result": "ESTABLISHED", "reads": reads}


def s6_seal(doc, context):
    if "RESULTS.json" not in doc or "PUBLIC_KEY.pem" not in doc:
        return _invalid("bundle lacks RESULTS.json or PUBLIC_KEY.pem")
    results = _json(doc["RESULTS.json"])
    public = public_key_from_pem(doc["PUBLIC_KEY.pem"])
    if public is None:
        return _invalid("PUBLIC_KEY.pem is not an Ed25519 SubjectPublicKeyInfo key")
    root = bytes.fromhex(results["S5_evidence_root"]["merkle_root_sha256"])
    seal = bytes.fromhex(results["S6_hmac_seal"]["seal_hex"])
    reads = ["RESULTS.json", "PUBLIC_KEY.pem"]
    if not ed25519_verify(public, root, seal):
        return {"result": "CONTRADICTED", "reads": reads}
    if ed25519_verify(public, _flip_last(root), seal) or ed25519_verify(public, root.hex().encode(), seal):
        return {"result": "NOT_ESTABLISHED", "reads": reads,
                "unresolved_obligations": ["seal verified over a changed root or over the hex text form"]}
    return {"result": "ESTABLISHED", "reads": reads}


RESULTS_PATH = "conformance/witness/RESULTS.json"
FIXTURE_PATH = "conformance/witness_generator/sample_evidence.json"


def s4_digests(doc, context):
    if RESULTS_PATH not in doc:
        return _invalid(f"{RESULTS_PATH} is not in the bundle")
    results = _json(doc[RESULTS_PATH])
    reads = [RESULTS_PATH, FIXTURE_PATH]
    if results["seal_scope"]["evidence_file"] != FIXTURE_PATH or FIXTURE_PATH not in doc:
        return {"result": "NOT_ESTABLISHED", "reads": [RESULTS_PATH],
                "unresolved_obligations": ["the declared evidence file is not the pinned fixture"]}
    raw = doc[FIXTURE_PATH]
    expected = [("evidence_package.json", raw)] + [
        (a["name"], a["content_utf8"].encode("utf-8")) for a in _json(raw).get("artifacts", [])]
    published = results["S4_file_integrity"]
    ok = len(published) == len(expected) and all(
        e["name"] == name and e["sha256"] == hashlib.sha256(data).hexdigest() and e["bytes"] == len(data)
        for e, (name, data) in zip(published, expected))
    return {"result": "ESTABLISHED" if ok else "CONTRADICTED", "reads": reads}


def s5_root(doc, context):
    if RESULTS_PATH not in doc:
        return _invalid(f"{RESULTS_PATH} is not in the bundle")
    results = _json(doc[RESULTS_PATH])
    digests = [bytes.fromhex(e["sha256"]) for e in results["S4_file_integrity"]]
    root, levels = merkle_documented(digests)
    published = results["S5_evidence_root"]
    ok = (root.hex() == published["merkle_root_sha256"] and published["leaf_count"] == len(digests)
          and [[h.hex() for h in lv] for lv in levels] == published["levels"])
    return {"result": "ESTABLISHED" if ok else "CONTRADICTED", "reads": [RESULTS_PATH]}


MANIFEST_PATH = "conformance/witness/MANIFEST.json"


def manifest_hashes(doc, context):
    if MANIFEST_PATH not in doc:
        return _invalid(f"{MANIFEST_PATH} is not in the bundle")
    manifest = _json(doc[MANIFEST_PATH])
    entries = list(manifest.get("nti_test_scripts", [])) + list(manifest.get("witness_generator", []))
    missing = [e["path"] for e in entries if e["path"] not in doc]
    if missing:
        return {"result": "NOT_ESTABLISHED", "reads": [MANIFEST_PATH],
                "unresolved_obligations": [f"listed file not pinned: {p}" for p in missing]}
    ok = all(hashlib.sha256(doc[e["path"]]).hexdigest() == e["sha256"] for e in entries)
    return {"result": "ESTABLISHED" if ok else "CONTRADICTED", "reads": [MANIFEST_PATH, "manifest-listed files"]}


def pages_mirror(doc, context):
    a, b = "conformance/witness/", "docs/witness/"
    names = sorted(k[len(a):] for k in doc if k.startswith(a))
    if not names or not any(k.startswith(b) for k in doc):
        return _invalid("bundle lacks conformance/witness or docs/witness")
    signed_same = all(doc.get(b + n) == doc.get(a + n) for n in SIGNED)
    shared_same = all(doc[a + n] == doc[b + n] for n in names if b + n in doc)
    return {"result": "ESTABLISHED" if signed_same and shared_same else "CONTRADICTED",
            "reads": ["conformance/witness/*", "docs/witness/*"]}


def suite_outcomes_evidenced(doc, context):
    if RESULTS_PATH not in doc:
        return _invalid(f"{RESULTS_PATH} is not in the bundle")
    _json(doc[RESULTS_PATH])
    return {"result": "NOT_ESTABLISHED", "reads": [RESULTS_PATH],
            "unresolved_obligations": ["a test transcript or CI attestation bound to the pinned commit",
                                       "an independent rerun of the pinned Rust and Python suites"]}


def key_anchor(doc, context):
    pem = doc.get("conformance/witness/PUBLIC_KEY.pem")
    if pem is None or public_key_from_pem(pem) is None:
        return _invalid("no Ed25519 PUBLIC_KEY.pem in the witness directory")
    return {"result": "NOT_ESTABLISHED", "reads": ["conformance/witness/PUBLIC_KEY.pem"],
            "unresolved_obligations": ["publication of the key outside the repository it signs",
                                       "a key custody and rotation statement"]}


# --- probes (one record per probe over all of its inputs) ---------------------------

README_PATH = "conformance/witness/README.md"
GENERATOR_PATH = "conformance/witness_generator/generate_seals.py"
VERIFY_PATH = "conformance/witness/verify.sh"
README_RULE = "Odd nodes are promoted unchanged"
GENERATOR_RULE = "right = level[i + 1] if i + 1 < len(level) else level[i]"
VERIFY_RULE = "(lv[i+1] if i+1 < len(lv) else lv[i])"


def s5_documented_vs_implemented(docs, context):
    tree = docs["tree"]
    if any(p not in tree for p in (README_PATH, GENERATOR_PATH, VERIFY_PATH, RESULTS_PATH)):
        return _invalid("README, generator, verifier or RESULTS.json is not pinned")
    lines = {"readme_rule_line": _line_of(tree[README_PATH], README_RULE),
             "generator_rule_line": _line_of(tree[GENERATOR_PATH], GENERATOR_RULE),
             "verifier_rule_line": _line_of(tree[VERIFY_PATH], VERIFY_RULE)}
    differ = [n for n in range(1, 9)
              if merkle_documented(probe_leaves(n))[0] != merkle_duplicating(probe_leaves(n))[0]]
    rfc_equal = all(merkle_documented(probe_leaves(n))[0] == merkle_rfc6962(probe_leaves(n)) for n in range(1, 9))
    published = [bytes.fromhex(e["sha256"]) for e in _json(tree[RESULTS_PATH])["S4_file_integrity"]]
    same_on_published = merkle_documented(published)[0] == merkle_duplicating(published)[0]
    witness = {**lines,
               "readme_sha256": hashlib.sha256(tree[README_PATH]).hexdigest(),
               "generator_sha256": hashlib.sha256(tree[GENERATOR_PATH]).hexdigest(),
               "verifier_sha256": hashlib.sha256(tree[VERIFY_PATH]).hexdigest(),
               "leaf_counts_where_roots_differ_1_to_8": differ,
               "documented_rule_equals_rfc6962_split_1_to_8": rfc_equal,
               "published_leaf_count": len(published),
               "published_root_same_under_both_rules": same_on_published,
               "vector_leaves": "sha256(b'nti-probe-leaf-<i>') for i = 1..n",
               "vectors": [{"n": n, "documented_root": merkle_documented(probe_leaves(n))[0].hex(),
                            "implemented_root": merkle_duplicating(probe_leaves(n))[0].hex()} for n in (3, 5, 6, 7)]}
    demonstrated = all(lines.values()) and bool(differ)
    message = ("The README states that an odd node is promoted unchanged; the published generator and verify.sh "
               "pair an odd last node with itself. The two rules give different roots for leaf counts "
               f"{', '.join(map(str, differ))} and the same root for the published {len(published)}-leaf tree."
               if demonstrated else "The documented and implemented rules were not both found, or never differ.")
    return {"observation": "DEMONSTRATED" if demonstrated else "NOT_DEMONSTRATED",
            "reads": [README_PATH, GENERATOR_PATH, VERIFY_PATH, RESULTS_PATH],
            "witness": witness, "affects_pinned_artifact": not same_on_published, "message": message}


def s5_leaf_count_binding(docs, context):
    tree = docs["tree"]
    if RESULTS_PATH not in tree:
        return _invalid(f"{RESULTS_PATH} is not pinned")
    results = _json(tree[RESULTS_PATH])
    pairs = []
    for n in (3, 5, 7):
        leaves = probe_leaves(n)
        a = merkle_duplicating(leaves)[0]
        b = merkle_duplicating(leaves + [leaves[-1]])[0]
        pairs.append({"leaf_count": n, "with_last_leaf_repeated": n + 1, "root": a.hex(),
                      "root_with_repeat": b.hex(), "collide": a == b})
    published_sizes = [len(lv) for lv in results["S5_evidence_root"]["levels"]]
    duplication_used = any(size % 2 == 1 and size > 1 for size in published_sizes)
    collides = all(p["collide"] for p in pairs)
    witness = {"vector_leaves": "sha256(b'nti-probe-leaf-<i>') for i = 1..n",
               "pairs": pairs,
               "s6_signs": results["S6_hmac_seal"]["signed_over"],
               "s6_message_bytes": 32,
               "leaf_count_inside_s6_message": False,
               "published_level_sizes": published_sizes,
               "published_tree_used_duplication": duplication_used,
               "rfc6962_split_collides_on_same_pairs": any(
                   merkle_rfc6962(probe_leaves(n)) == merkle_rfc6962(probe_leaves(n) + [probe_leaves(n)[-1]])
                   for n in (3, 5, 7))}
    message = ("Under the implemented rule a list of n leaves and the same list with its last leaf repeated have "
               "the same root (n = 3, 5, 7), and S6 signs only the 32-byte root, so the seal does not bind the "
               "leaf count. The published tree has even sizes at every level, so it is not affected."
               if collides else "No collision was found for the tested leaf counts.")
    return {"observation": "DEMONSTRATED" if collides else "NOT_DEMONSTRATED", "reads": [RESULTS_PATH],
            "witness": witness, "affects_pinned_artifact": collides and duplication_used, "message": message}


def s6_message_binding(docs, context):
    pkg = _package(docs["witness"])
    if pkg is None:
        return _invalid("witness bundle is incomplete")
    public = public_key_from_pem(pkg["PUBLIC_KEY.pem"])
    results = _json(pkg["RESULTS.json"])
    original_name = results["S4_file_integrity"][1]["name"]
    results["seal_scope"]["classification"] = "PRODUCTION"
    results["S4_file_integrity"][1]["name"] = "payment_authorization.json"
    relabelled = (json.dumps(results, indent=2) + "\n").encode("utf-8")
    digests = [bytes.fromhex(e["sha256"]) for e in results["S4_file_integrity"]]
    root = merkle_documented(digests)[0]
    seal = bytes.fromhex(results["S6_hmac_seal"]["seal_hex"])
    s6_ok = ed25519_verify(public, root, seal) and root.hex() == results["S5_evidence_root"]["merkle_root_sha256"]
    pkg_ok = ed25519_verify(public, relabelled + pkg["MANIFEST.json"], pkg["SIGNATURE.sig"])
    witness = {"changed": {"seal_scope.classification": ["SYNTHETIC - test fixture, not production evidence",
                                                         "PRODUCTION"],
                           "S4_file_integrity[1].name": [original_name, "payment_authorization.json"]},
               "relabelled_results_sha256": hashlib.sha256(relabelled).hexdigest(),
               "s5_root_after_relabel": root.hex(),
               "s6_seal_verifies_after_relabel": s6_ok,
               "package_signature_verifies_after_relabel": pkg_ok,
               "fields_bound_by_s6": ["S5_evidence_root.merkle_root_sha256"],
               "fields_not_bound_by_s6": ["S4 artifact names", "S4 byte counts", "S5 leaf_count",
                                          "seal_scope.classification", "scope", "suites"]}
    demonstrated = s6_ok and not pkg_ok
    message = ("After relabelling the fixture PRODUCTION and renaming an artifact, the S5 root is unchanged and "
               "the S6 seal still verifies; only the outer package signature fails. The seal alone can be "
               "carried into a context that misdescribes what it covers."
               if demonstrated else "The relabel was caught by the S6 seal, or the package signature still verified.")
    return {"observation": "DEMONSTRATED" if demonstrated else "NOT_DEMONSTRATED",
            "reads": ["RESULTS.json", "MANIFEST.json", "SIGNATURE.sig", "PUBLIC_KEY.pem"],
            "witness": witness, "affects_pinned_artifact": demonstrated, "message": message}


def package_signature_framing(docs, context):
    pkg = _package(docs["witness"])
    if pkg is None:
        return _invalid("witness bundle is incomplete")
    public = public_key_from_pem(pkg["PUBLIC_KEY.pem"])
    results, manifest = pkg["RESULTS.json"], pkg["MANIFEST.json"]
    if not results.endswith(b"\n"):
        return {"observation": "NOT_DEMONSTRATED", "reads": ["RESULTS.json", "MANIFEST.json"], "witness": {},
                "affects_pinned_artifact": False, "message": "RESULTS.json has no trailing newline to move."}
    shifted_r, shifted_m = results[:-1], b"\n" + manifest
    try:
        json.loads(shifted_r)
        json.loads(shifted_m)
        both_parse = True
    except ValueError:
        both_parse = False
    verifies = ed25519_verify(public, shifted_r + shifted_m, pkg["SIGNATURE.sig"])
    witness = {"results_sha256": hashlib.sha256(results).hexdigest(),
               "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
               "shifted_results_sha256": hashlib.sha256(shifted_r).hexdigest(),
               "shifted_manifest_sha256": hashlib.sha256(shifted_m).hexdigest(),
               "both_shifted_files_are_strict_json": both_parse,
               "signature_verifies_on_shifted_pair": verifies,
               "signed_message": "RESULTS.json || MANIFEST.json, no length prefix or separator"}
    demonstrated = verifies and both_parse
    message = ("Moving the final newline of RESULTS.json to the start of MANIFEST.json gives two different files, "
               "both strict JSON, that verify under the same signature. The boundary between the signed files is "
               "not authenticated; with strict parsers only whitespace can move."
               if demonstrated else "The shifted pair did not verify or did not parse.")
    return {"observation": "DEMONSTRATED" if demonstrated else "NOT_DEMONSTRATED",
            "reads": ["RESULTS.json", "MANIFEST.json", "SIGNATURE.sig", "PUBLIC_KEY.pem"],
            "witness": witness, "affects_pinned_artifact": demonstrated, "message": message}


def key_reuse_without_context(docs, context):
    pkg = _package(docs["witness"])
    if pkg is None:
        return _invalid("witness bundle is incomplete")
    public = public_key_from_pem(pkg["PUBLIC_KEY.pem"])
    results = _json(pkg["RESULTS.json"])
    root = bytes.fromhex(results["S5_evidence_root"]["merkle_root_sha256"])
    both = (ed25519_verify(public, pkg["RESULTS.json"] + pkg["MANIFEST.json"], pkg["SIGNATURE.sig"])
            and ed25519_verify(public, root, bytes.fromhex(results["S6_hmac_seal"]["seal_hex"])))
    witness = {"public_key_raw_hex": public.hex(),
               "package_signature_message_bytes": len(pkg["RESULTS.json"]) + len(pkg["MANIFEST.json"]),
               "s6_message_hex": root.hex(), "s6_message_bytes": len(root),
               "s6_message_has_context_prefix": False,
               "same_key_verifies_both": both}
    message = ("One Ed25519 key signs both the package and the S6 seal, and the S6 message is the bare 32-byte "
               "root with no context string, so any 32-byte value this key ever signs reads as a valid S6 seal."
               if both else "The same key did not verify both signatures.")
    return {"observation": "DEMONSTRATED" if both else "NOT_DEMONSTRATED",
            "reads": ["RESULTS.json", "MANIFEST.json", "SIGNATURE.sig", "PUBLIC_KEY.pem"],
            "witness": witness, "affects_pinned_artifact": both, "message": message}


def key_changed_between_revisions(docs, context):
    now, then = _package(docs["witness"]), _package(docs["history_witness"])
    if now is None or then is None:
        return _invalid("a witness bundle is incomplete")
    key_now, key_then = public_key_from_pem(now["PUBLIC_KEY.pem"]), public_key_from_pem(then["PUBLIC_KEY.pem"])
    readme = docs["witness"].get("README.md", b"")
    witness = {"pinned_key_raw_hex": key_now.hex(),
               "earlier_key_raw_hex": key_then.hex(),
               "pinned_key_pem_sha256": hashlib.sha256(now["PUBLIC_KEY.pem"]).hexdigest(),
               "earlier_key_pem_sha256": hashlib.sha256(then["PUBLIC_KEY.pem"]).hexdigest(),
               "earlier_package_verifies_under_earlier_key": ed25519_verify(
                   key_then, then["RESULTS.json"] + then["MANIFEST.json"], then["SIGNATURE.sig"]),
               "pinned_package_verifies_under_pinned_key": ed25519_verify(
                   key_now, now["RESULTS.json"] + now["MANIFEST.json"], now["SIGNATURE.sig"]),
               "pinned_readme_mentions_rotation": "rotat" in readme.decode("utf-8", errors="replace").lower()}
    changed = key_now != key_then
    message = ("The witness key differs between the two pinned revisions and each package verifies under its own "
               "key. Nothing in the pinned package records the change, so a verifier holding only the repository "
               "cannot tell which key is authoritative." if changed else "The key is the same in both revisions.")
    return {"observation": "DEMONSTRATED" if changed else "NOT_DEMONSTRATED",
            "reads": ["PUBLIC_KEY.pem", "RESULTS.json", "MANIFEST.json", "SIGNATURE.sig", "README.md"],
            "witness": witness, "affects_pinned_artifact": changed, "message": message}


EXTERNAL_MARKERS = ("Raja549h/asl-conformance-kit", "ASL")
NATIVE_CLAIM = "It shares no code with any external conformance kit."
SPEC_REFERENCE = "to match the witness specification"


TEXT_SUFFIXES = (".md", ".json", ".py", ".sh", ".html", ".txt")


def _naming(bundle, marker):
    """Text files of a bundle that contain marker (binary files such as SIGNATURE.sig are skipped)."""
    return sorted(p for p, data in bundle.items() if p.endswith(TEXT_SUFFIXES) and marker.encode() in data)


def seal_scheme_attribution(docs, context):
    now, then = docs["witness"], docs["history_witness"]
    found_then = {m: _naming(then, m) for m in EXTERNAL_MARKERS}
    found_now = {m: _naming(now, m) for m in EXTERNAL_MARKERS}
    readme = now.get("README.md", b"")
    witness = {"earlier_revision_files_naming": found_then,
               "pinned_revision_files_naming": found_now,
               "pinned_readme_states_native": NATIVE_CLAIM in _normalised(readme),
               "pinned_readme_refers_to_witness_specification": SPEC_REFERENCE in _normalised(readme),
               "pinned_readme_sha256": hashlib.sha256(readme).hexdigest()}
    demonstrated = (all(found_then.values()) and not any(found_now.values())
                    and witness["pinned_readme_refers_to_witness_specification"])
    message = ("An earlier revision of the witness package named the external ASL project "
               "(Raja549h/asl-conformance-kit) as the source of the S4/S5/S6 seals. The pinned revision keeps the "
               "S4/S5/S6 names and refers to 'the witness specification' but names no source for it."
               if demonstrated else "The attribution pattern was not observed.")
    return {"observation": "DEMONSTRATED" if demonstrated else "NOT_DEMONSTRATED",
            "reads": ["README.md", "MANIFEST.json", "RESULTS.json", "vendor/*"],
            "witness": witness, "affects_pinned_artifact": demonstrated, "message": message}
