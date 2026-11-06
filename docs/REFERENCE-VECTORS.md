# Reference vectors

`vectors/aacp-reference-vectors-v1/` is a frozen, digest-pinned set of 86
input and expected-answer pairs for nine deterministic AACP operations. A
separately written implementation, in any language, can be checked against it
without importing or running anything from this repository. The suite also
checks this repository's own reference rules.

The vectors test agreement on these cases. They do not award a property
verdict. Read [What agreement establishes](#what-agreement-establishes) before
you cite a run.

## Verify the bytes first

The suite is frozen, and its bytes are pinned three ways. Each file's SHA-256
is listed in `MANIFEST.json`. `SHA256SUMS` lists every file, and also the
manifest. `tests/test_vectors.py` pins the manifest's digest. Check them with
no AACP code at all:

```sh
cd vectors/aacp-reference-vectors-v1
sha256sum --check SHA256SUMS        # macOS: shasum -a 256 -c SHA256SUMS
```

The same check, with the manifest cross-checked as well:

```sh
python -m conformance.vectors verify
```

`python scripts/build_reference_vectors.py --check` rebuilds the suite in
memory from its sources and compares the bytes. It fails if a source fixture,
a producer artifact or a hand-written expectation has changed. A frozen suite
is never rewritten: `--write` refuses an existing directory. A change means a
new suite version, which leaves v1 in place.

## Where each expected answer comes from

Every vector names its source in `expected_source`, and the source is one of
three kinds:

| Prefix | Source |
|---|---|
| `fixture:` | a committed, hand-authored fixture, copied verbatim (the 21 E-rule fixtures, the three adversarial assessments) |
| `producer:` | another project's published or signed expectation (AgentAvow's key pairs, issuer-signed tool digests and six binding outcomes; the RFC189 OE-08 case) |
| `specification:` | normative text in this repository, written out by hand in `scripts/build_reference_vectors.py` |

The build script imports none of the rules it checks, and a test enforces
that. An expectation computed by the implementation under test would test
nothing. Agreement with the reference was then checked separately, with
`python -m conformance.vectors check`. The canonical-JSON digests were
also recomputed with `shasum`, outside Python.

## The operations

Each vector file states its operation's contract in `contract`. In summary:

| Operation | Vectors | Input | Result |
|---|---:|---|---|
| `e_rule.evaluate` | 21 | an execution-boundary-input-v0.2 document | the verdict object; `INVALID_INPUT` and `UNSUPPORTED` are non-verdicts returned as results |
| `oe08.observation_vantage` | 15 | `{record, trusted_control_domains}` | `{result, unmet_obligation, reason}`, compared on the keys in `compare` |
| `agentavow.tool_key` | 13 | `{name}` | the `tool:` map key |
| `agentavow.tool_digest` | 4 | `{tool}` | `sha256:` plus the hex digest of the tool definition |
| `agentavow.binding` | 6 | `{vector: {gate, jws}, fixture: {issuer, attestation}}` | the six axes and `rely`; needs Ed25519 |
| `lab.canonical_json` | 11 | `{text}`, a JSON document in its own key order | `{canonical_utf8, sha256}` |
| `lab.read_json` | 5 | `{text}` | the value, or `DUPLICATE_KEY` or `INVALID_JSON` |
| `lab.forbidden_keys` | 5 | `{value}` | the locations of aggregate-like keys |
| `coverage.component_matrix` | 6 | `{assessment}` | the A to G matrix, or `COVERAGE_ERROR` or `INVALID_ASSESSMENT` |

Two of them carry a hazard an implementer should know first:

- **The lab's canonical form is not RFC 8785.** It is Python's
  `json.dumps(sort_keys=True, indent=2, ensure_ascii=False)` plus a newline.
  Keys sort by code point, not by UTF-16 unit
  (`canon-key-order-code-point`). Floats keep Python's repr, so `1.0`,
  `1e+100` and `-0.0` are written that way (`canon-float-forms`). A parser
  that drops a number's lexical form cannot reproduce that vector. That is
  the point of the vector, because such a parser cannot verify the digest of a
  lab package that holds floats either.
- **A repeated component is a schema error, not a coverage error.** The v0.2
  schema allows each of A to G at most once (`maxContains: 1`), so it refuses
  a repeated row before the coverage check runs (`cov-duplicate-component`).

## The protocol

`run` starts the implementation once per vector. It writes one JSON request
to the implementation's standard input:

```json
{"operation": "lab.read_json", "vector_id": "read-duplicate-nested", "input": {"text": "{\"a\": {\"x\": 1, \"x\": 1}}"}}
```

The implementation writes one JSON line to standard output and exits 0:

```json
{"error": "DUPLICATE_KEY"}
```

The answer is either `{"result": ...}` or `{"error": "<CODE>"}`. A line ends at
`\n` only, so a literal U+2028 inside a JSON string is part of the line. An
operation the implementation does not cover answers
`{"error": "UNSUPPORTED_OPERATION"}`, which is reported as not implemented, not
as a failure.

```sh
python -m conformance.vectors run --impl "node my-aacp.js" --json report.json
python -m conformance.vectors run --impl "./my-aacp" --operations lab.canonical_json,lab.read_json
```

Comparison is strict JSON equality. `true` is not `1`, `1.0` is not `1`, and
an extra key disagrees. Where a vector lists `compare`, only those keys of the
result are judged. Each vector comes out as one of four outcomes:

| Outcome | Meaning | Fails the run |
|---|---|---|
| `AGREES` | the answer equals the expected answer | no |
| `DISAGREES` | a well-formed answer that differs | yes |
| `NOT_IMPLEMENTED` | `UNSUPPORTED_OPERATION` | no |
| `ERROR` | a non-zero exit, a timeout, no line or several lines, or text that is not JSON | yes |

`run` executes the command it is given and nothing else. It fetches and
installs nothing, and it passes the request on standard input only. Running a
third party's binary is the operator's decision, under the same rules as
[AGENTS.md](../AGENTS.md).

Two implementations ship with the suite:

- **The reference.** `python -m conformance.vectors serve` is the reference
  speaking the protocol, so the protocol itself is exercised end to end.
- **A stdlib example.** `templates/vector-impl/stdlib_impl.py` is a
  standard-library implementation of six operations. It was written from the
  contracts and imports nothing from `conformance`. It is a template for
  another language. It is **not** an independent implementation, because the
  same project wrote it.

## Do the vectors notice a wrong implementation?

`tests/test_vectors_adequacy.py` seeds 34 faults that a second implementer
could plausibly make. 26 are applied to the stdlib example and eight to the
reference's answer, for the operations the example does not cover. Every one
must make at least one vector disagree. Among them:

- canonical JSON with ASCII escapes, with no final newline, with RFC 8785 key
  order, with unsorted keys, or with integral floats written as integers;
- duplicate keys accepted, or caught at the top level only;
- an aggregate key missed or matched by substring;
- a tool digest that hashes `_meta`, drops the profile tag or uses spaced JSON;
- a vantage rule that trusts the record's own independence claim or
  control-domain label;
- a binding check that skips the signature or the expiry;
- a coverage matrix that adds a score.

The unsorted-keys fault survived the first version of the suite. The vector
files sort their keys, so a parsed input arrived already sorted. The
canonical-JSON vectors now take the document as JSON text, and the fault is
killed. The E rule's 30 seeded faults are in `conformance/mutations-v0.2.json`
and run against the same fixtures the E vectors copy
([MUTATIONS-AND-INVARIANTS.md](../MUTATIONS-AND-INVARIANTS.md)).

## What agreement establishes

Agreement on every vector of an operation establishes exactly this: on these
86 committed inputs, the implementation gives the answers stated here, under
the stated comparison.

It does **not** establish:

- any property verdict, A to G, for the implementation or for a system that
  uses it;
- correctness on inputs outside the suite, which mutation and invariant
  checks bound but do not close;
- the security of a deployed product, or the authenticity of evidence fed
  to the rules. The E rule and the vantage rule trust their accepted premises
  ([SPECIFICATION-v0.2.md](../SPECIFICATION-v0.2.md#6-bounded-reference-rule-and-corpus));
- independence. A run by this repository's authors, or of code they wrote, is
  a reproduction ([METHOD.md](../METHOD.md)). Record the implementer and the
  operator by their actual identities.

A run report lists outcomes per vector and per operation. It holds no score,
total or grade, and a count of agreeing vectors is not a conformance level.

## Not covered

- **NaN and Infinity.** Python's `json.loads` accepts them, so `lab.read_json`
  does too, and JSON cannot state the resulting value. No vector covers this.
- **The lab's packaging.** File-tree hashing, the run manifest and leak
  scanning are tested in `tests/lab/`, not as portable vectors.
- **AgentAvow beyond its published vectors.** The binding vectors are the
  producer's six. Other JWS edge cases are the producer's to publish.
