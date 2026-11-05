"""Do the reference vectors notice a wrong implementation?

Each fault below is a mistake a second implementer could plausibly make. It is
applied in memory to the standard-library example implementation
(templates/vector-impl/stdlib_impl.py) or to the reference's answer, and at
least one vector of that operation must then disagree. A fault no vector
notices is a gap in the suite, reported by name. The E rule's own seeded faults
live in conformance/mutations-v0.2.json and run against the same fixtures the
E vectors copy.
"""

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

from conformance import vectors as V

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stdlib_impl", ROOT / "templates" / "vector-impl" / "stdlib_impl.py")
impl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(impl)


def _canon(**kw):
    def fault(text_in):
        value = json.loads(text_in)
        options = {"sort_keys": True, "indent": 2, "ensure_ascii": False}
        options.update(kw.get("_options", {}))
        text = json.dumps(value, **options) + kw.get("_end", "\n")
        return {"result": {"canonical_utf8": text,
                           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}}
    return fault


def _rfc8785_like(text_in):
    value = json.loads(text_in)
    # Sort keys by UTF-16 code units, as RFC 8785 does; otherwise the lab's form.
    def order(obj):
        if isinstance(obj, dict):
            return {k: order(obj[k]) for k in sorted(obj, key=lambda s: s.encode("utf-16-be"))}
        if isinstance(obj, list):
            return [order(x) for x in obj]
        return obj
    text = json.dumps(order(value), indent=2, ensure_ascii=False) + "\n"
    return {"result": {"canonical_utf8": text,
                       "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}}


def _float_as_int(text_in):
    value = json.loads(text_in)
    def walk(obj):
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        if isinstance(obj, float) and obj.is_integer():
            return int(obj)
        return obj
    return impl.canonical_json(walk(value))


def _vantage_fault(name):
    def fault(record, trusted):
        out = impl.vantage(record, trusted)
        verdict = out["result"]
        if name == "trust-declared-independence" and isinstance(record, dict) \
                and record.get("declared_independence") is True:
            return {"result": {"result": "ESTABLISHED", "unmet_obligation": None,
                               "reason": "independent-vantage-established"}}
        if name == "trust-record-domains" and verdict["reason"] == \
                "observation-vantage-not-established" and isinstance(record, dict) \
                and record.get("control_domain") and record.get("observed_control_domain") \
                and record.get("control_domain") != record.get("observed_control_domain"):
            return {"result": {"result": "ESTABLISHED", "unmet_obligation": None,
                               "reason": "independent-vantage-established"}}
        if name == "missing-facts-as-false" and verdict["reason"] == \
                "observation-vantage-not-established" and isinstance(record, dict) \
                and record.get("control_domain") in set(trusted):
            return {"result": {"result": "ESTABLISHED", "unmet_obligation": None,
                               "reason": "independent-vantage-established"}}
        if name == "invalid-as-not-established" and verdict["result"] == "INVALID_INPUT":
            return {"result": {"result": "NOT_ESTABLISHED", "unmet_obligation":
                               "observation_vantage", "reason": "x"}}
        if name == "no-obligation-named" and verdict["unmet_obligation"]:
            return {"result": {**verdict, "unmet_obligation": None}}
        return out
    return fault


def _digest_fault(name):
    def fault(tool):
        if name == "hash-meta":
            selected = {k: v for k, v in tool.items() if v is not None}
        elif name == "drop-annotations-and-schemas":
            selected = {k: tool[k] for k in ("name", "title", "description") if k in tool}
        else:
            selected = {k: tool[k] for k in ("name", "title", "description", "inputSchema",
                                             "outputSchema", "annotations") if k in tool}
        preimage = {"profile": "agentavow.mcp-tool-definition.v1", "tool": selected}
        if name == "spaced-json":
            data = json.dumps(preimage, sort_keys=True, ensure_ascii=False)
        elif name == "no-profile":
            data = json.dumps(selected, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        else:
            data = json.dumps(preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()
    return fault


def _key_fault(name):
    def fault(value):
        if name == "keep-percent":
            out = ""
            for ch in value:
                out += ch if 0x21 <= ord(ch) <= 0x7E and ch != "=" else "".join(
                    f"%{b:02X}" for b in ch.encode("utf-8"))
            return "tool:" + out
        if name == "lowercase-hex":
            return impl.tool_key(value).lower().replace("tool:", "tool:", 1) \
                if "%" in impl.tool_key(value) else impl.tool_key(value)
        if name == "no-truncation":
            body = impl.tool_key(value)[5:]
            return "tool:" + (body if "~" not in body else "".join(
                ch if 0x21 <= ord(ch) <= 0x7E and ch not in "%=" else f"%{ord(ch):02X}"
                for ch in value))
        if name == "code-point-escape":
            return "tool:" + "".join(ch if 0x21 <= ord(ch) <= 0x7E and ch not in "%=" else
                                     f"%{ord(ch):02X}" for ch in value)[:128]
        return impl.tool_key(value)
    return fault


IMPL_FAULTS = {
    "lab.canonical_json": {
        "ascii-escapes": _canon(_options={"ensure_ascii": True}),
        "no-final-newline": _canon(_end=""),
        "compact-separators": _canon(_options={"indent": None, "separators": (",", ":")}),
        "unsorted-keys": _canon(_options={"sort_keys": False}),
        "rfc8785-key-order": _rfc8785_like,
        "integral-floats-as-integers": _float_as_int,
    },
    "lab.read_json": {
        "duplicates-allowed": lambda text: impl.read_json(text) if '"a": 1, "a"' not in text
        and '"x": 1, "x"' not in text else {"result": json.loads(text)},
        "only-top-level-duplicates": lambda text: {"result": json.loads(text)}
        if '"x": 1, "x"' in text else impl.read_json(text),
        "trailing-comma-accepted": lambda text: {"result": {"a": 1}}
        if text == '{"a": 1,}' else impl.read_json(text),
    },
    "lab.forbidden_keys": {
        "misses-grade": lambda value: [p for p in impl.forbidden_keys(value)
                                       if not p.endswith(".grade")],
        "case-insensitive": lambda value: impl.forbidden_keys(value) + (
            ["$.Total"] if isinstance(value, dict) and "Total" in value else []),
        "substring-match": lambda value: impl.forbidden_keys(value) + (
            ["$.scoreboard"] if isinstance(value, dict) and "scoreboard" in value else []),
        "top-level-only": lambda value: [p for p in impl.forbidden_keys(value)
                                         if p.count(".") == 1 and "[" not in p],
        "dotted-list-index": lambda value: [p.replace("[1]", ".1")
                                            for p in impl.forbidden_keys(value)],
    },
    "agentavow.tool_key": {k: _key_fault(k) for k in (
        "keep-percent", "no-truncation", "code-point-escape")},
    "agentavow.tool_digest": {k: _digest_fault(k) for k in (
        "hash-meta", "drop-annotations-and-schemas", "spaced-json", "no-profile")},
    "oe08.observation_vantage": {k: _vantage_fault(k) for k in (
        "trust-declared-independence", "trust-record-domains", "missing-facts-as-false",
        "invalid-as-not-established", "no-obligation-named")},
}

#: Faults on the reference's answer, for the operations the example does not implement.
REFERENCE_FAULTS = {
    "coverage.component_matrix": {
        "missing-row-allowed": lambda inp, ans: {"result": {"components": []}}
        if ans.get("error") == "COVERAGE_ERROR" else ans,
        "schema-error-as-coverage": lambda inp, ans: {"error": "COVERAGE_ERROR"}
        if ans.get("error") == "INVALID_ASSESSMENT" else ans,
        "evidence-tier-dropped": lambda inp, ans: {"result": {**ans["result"], "components": [
            {k: v for k, v in c.items() if k != "evidence_tier"}
            for c in ans["result"]["components"]]}} if "result" in ans else ans,
        "score-added": lambda inp, ans: {"result": {**ans["result"], "score": 7}}
        if "result" in ans else ans,
    },
    "agentavow.binding": {
        "signature-not-checked": lambda inp, ans: {"result": {**ans["result"],
                                                               "signature_valid": True,
                                                               "rely": all(v is True for k, v in {
                                                                   **ans["result"],
                                                                   "signature_valid": True}.items()
                                                                   if k != "rely")}},
        "expiry-ignored": lambda inp, ans: {"result": {**ans["result"], "fresh": True,
                                                       "rely": all(v is True for k, v in {
                                                           **ans["result"], "fresh": True}.items()
                                                           if k != "rely")}},
        "not-evaluated-as-false": lambda inp, ans: {"result": {
            **ans["result"], "tool_digest_binds": False}}
        if ans["result"]["tool_digest_binds"] == "not_evaluated" else ans,
    },
    "e_rule.evaluate": {
        "non-verdict-as-not-established": lambda inp, ans: {"result": {
            "verification_status": "COMPLETED", "status": "NOT_ESTABLISHED"}}
        if ans["result"].get("status") is None else ans,
    },
}


class VectorAdequacy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ops = {d["operation"]: d for d in V.load_operations()}
        cls.reference = V._reference()

    def _disagreements(self, operation, respond):
        rows = V.judge(self.ops[operation], respond)
        return [r["id"] for r in rows if r["outcome"] == V.DISAGREES]

    def test_the_unfaulted_example_agrees(self):
        for operation in IMPL_FAULTS:
            with self.subTest(operation=operation):
                self.assertEqual(self._disagreements(operation, impl.respond), [])

    def test_every_implementation_fault_is_noticed(self):
        survivors = []
        for operation, faults in IMPL_FAULTS.items():
            argument = {"lab.canonical_json": "text", "lab.read_json": "text",
                        "lab.forbidden_keys": "value", "agentavow.tool_key": "name",
                        "agentavow.tool_digest": "tool"}.get(operation)
            for name, fault in faults.items():
                if operation == "oe08.observation_vantage":
                    respond = lambda r, f=fault: f(r["input"]["record"],  # noqa: E731
                                                   r["input"]["trusted_control_domains"])
                else:
                    def respond(r, f=fault, a=argument, op=operation):
                        out = f(r["input"][a])
                        return out if op in ("lab.canonical_json", "lab.read_json") \
                            else {"result": out}
                if not self._disagreements(operation, respond):
                    survivors.append(f"{operation}:{name}")
        self.assertEqual(survivors, [], "faults no vector notices")

    def test_every_reference_fault_is_noticed(self):
        survivors = []
        for operation, faults in REFERENCE_FAULTS.items():
            for name, fault in faults.items():
                def respond(r, f=fault):
                    return f(r["input"], V.answer(r, self.reference))
                if not self._disagreements(operation, respond):
                    survivors.append(f"{operation}:{name}")
        self.assertEqual(survivors, [], "faults no vector notices")


if __name__ == "__main__":
    unittest.main()
