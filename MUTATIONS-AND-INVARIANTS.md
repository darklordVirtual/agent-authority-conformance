# Mutations and invariants for the bounded E rule

**Status:** draft, alongside v0.2. Two read-only adequacy checks for
`conformance/boundary.py` and the fixture corpus under `tests/fixtures/`.
Neither is a certification, a score, or a statement about any deployed system.

## Why two more checks

`python -m conformance.check` asks one question of the reference rule: does it
reproduce every committed fixture's expected result. A rule can pass that
question and still be wrong in a way no fixture reaches, and a fixture corpus
can pass it and still be too thin to notice a wrong rule. The two checks here
ask the complementary questions.

- `python -m conformance.mutations` asks how thin the corpus is. It seeds a
  small fault into the rule, in memory, and records whether any fixture
  notices. This is mutation analysis (DeMillo, Lipton and Sayward, 1978). A
  fault no fixture notices is a **survivor**: a gap in the corpus, never a
  defect in the rule.
- `python -m conformance.invariants` asks whether the rule keeps the
  relations the specification implies on inputs nobody authored. Each relation
  names a transformation of a document and the part of the verdict that must
  not change under it (metamorphic testing: Chen, Cheung and Yiu, 1998;
  Segura et al., 2016). A table-driven reference model of the v0.2 rule,
  written separately, must also agree with `evaluate` on every generated
  document (differential testing: McKeeman, 1998). Neither needs an expected
  answer per document, which is the oracle problem these methods exist for
  (Barr et al., 2015).

## Mutations

`conformance/mutations-v0.2.json` holds 30 faults and two controls. Each fault
replaces one exact anchor in `boundary.py` with one replacement, and the
anchor must occur exactly once. The classes:

| Class | Faults | What they break |
|---|---|---|
| `input_admission` | 3 | schema validation skipped; unsupported property mistaken for invalid input; the property check inverted |
| `scope` | 2 | attempts in another scope counted; only attempts in another scope counted |
| `envelope` | 2 | the verdict names the wrong scope or the wrong property |
| `bypass` | 4 | an observed bypass inverted, required of every attempt, made inconclusive, or ignored |
| `premises` | 6 | a premise's scope ignored or inverted; a premise dropped; obligation names or order swapped |
| `minimum_classes` | 8 | the subset check inverted, made strict or removed; each of the five minimum classes dropped |
| `outcomes` | 2 | an unknown outcome ignored or misread as blocked |
| `decision` | 3 | obligations never block; obligations dropped from the verdict; inconclusive reported as failure |

The positive control turns a bounded `PASS` into `FAIL` and must be killed;
the inert control edits a docstring and must survive. If either misbehaves the
harness stops with an error and reports no result, because the fixtures could
not then be trusted to see anything.

Result on this corpus: 30 killed, 0 survived, 0 declared equivalent, over 21
fixtures. Seven fixtures were added to reach that: one per missing minimum
class (`missing-<class>.json`), `extra-class-pass.json` (a sixth attempted
class leaves a bounded `PASS` unchanged) and `all-obligations-open.json`
(every obligation at once, in the declared order). Each was written after the
fault it kills was known, so the kill shows the repair, not generalisation.

A fault that cannot be killed under the rule's contract is declared with an
`equivalent` field and its reason. It stays in the file, is reported, and is
excluded from the survivor count. Deciding equivalence is undecidable in
general (Budd and Angluin, 1982), so a declaration is an argument, not a proof.

## Invariants

`conformance/invariants.py` generates every combination of the two premise
descriptors (absent, in scope, in another scope) with every subset of six
attempt classes (the five minimum ones plus one extra) up to five members,
each member in every outcome, plus one out-of-scope copy per non-empty set:
60,597 documents. Twelve relations run on each.

| ID | Relation |
|---|---|
| INV-1 | the verdict names property `E`, echoes the evaluation scope and has exactly the four envelope keys |
| INV-2 | the same input gives the same verdict, and the input is not mutated |
| INV-3 | the order of attempts never matters |
| INV-4 | an attempt in another scope never matters, even a reached effect |
| INV-5 | a reached effect in scope yields `FAIL` with no obligations, whatever else is present |
| INV-6 | removing an accepted premise never strengthens the verdict: `FAIL` stays, `PASS` becomes `NOT_ESTABLISHED` with that obligation, an inconclusive verdict gains it |
| INV-7 | an unknown outcome never yields `PASS` |
| INV-8 | a `PASS` loses to `NOT_ESTABLISHED` with `minimum_bypass_classes` when a needed minimum class is removed |
| INV-9 | obligations are empty on a decisive verdict, and on an inconclusive one they are non-empty, unique and in the declared order |
| INV-10 | an expected result in the input is refused before inference (`INVALID_INPUT`) |
| INV-11 | another property is a non-verdict (`UNSUPPORTED`), never a verdict |
| INV-12 | the reference model agrees with the rule |

Result: 0 failures on the generated space. The relations also hold on every
committed fixture input, and the space reaches all three verdicts and all four
obligations, so a relation is not vacuously true.

## What this does not establish

- Killing every seeded fault says nothing about faults nobody seeded. The
  fault set was written by the rule's author; a second party choosing faults
  without reading this file, and committing their sha256
  (`python -m conformance.mutations --hash` prints the digest of this set)
  before running, would be independent evidence. This set is not.
- A relation that holds on 60,597 generated documents holds on those
  documents. The generator is bounded (five attempts, six classes, two
  scopes); a document outside that space is unmeasured.
- The reference model and the rule share an author and a specification. Their
  agreement catches implementation slips in either; it cannot catch a
  misreading of the specification that both share.
- Nothing here inspects a deployment, authenticates evidence, or establishes
  observation coverage. The E rule consumes accepted evidence, and these
  checks consume the E rule.

## Sources

- DeMillo, R. A., Lipton, R. J., Sayward, F. G. (1978). Hints on Test Data Selection: Help for the Practicing Programmer. *IEEE Computer* 11(4):34-41.
- Budd, T. A., Angluin, D. (1982). Two notions of correctness and their relation to testing. *Acta Informatica* 18(1):31-45.
- Just, R., Jalali, D., Inozemtseva, L., Ernst, M. D., Holmes, R., Fraser, G. (2014). Are mutants a valid substitute for real faults in software testing? *FSE*.
- Chen, T. Y., Cheung, S. C., Yiu, S. M. (1998). Metamorphic testing: a new approach for generating next test cases. Technical Report HKUST-CS98-01.
- Segura, S., Fraser, G., Sanchez, A. B., Ruiz-Cortés, A. (2016). A Survey on Metamorphic Testing. *IEEE TSE* 42(9):805-824.
- Barr, E. T., Harman, M., McMinn, P., Shahbaz, M., Yoo, S. (2015). The Oracle Problem in Software Testing: A Survey. *IEEE TSE* 41(5):507-525.
- McKeeman, W. M. (1998). Differential Testing for Software. *Digital Technical Journal* 10(1):100-107.
