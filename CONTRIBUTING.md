# Contributing

Agent Authority Conformance is intentionally conservative. The project improves when a contribution makes a claim boundary sharper, an assessment more reproducible, or the model less dependent on one architecture.

## High-value contributions

- Apply A–G to a runtime that was not involved in designing the vocabulary.
- Provide a discriminating test that separates two properties currently being conflated.
- Show that a property definition is ambiguous, architecture-specific or unfalsifiable.
- Propose a missing property with a concrete case that cannot be represented by A–G.
- Replace `REPORTED` evidence with an immutable, independently resolvable artifact.
- Challenge a `PASS` whose evidence does not directly exercise the claimed property.

## Evidence rules

For a proposed `PASS`, include:

1. system version and immutable revision;
2. test, fixture, code path or committed result artifact;
3. reproduction command where applicable;
4. process/deployment scope;
5. real vs simulated effect declaration;
6. a caveat describing what the evidence does **not** establish.

README prose, architecture diagrams and marketing statements can provide context, but they are not sufficient direct evidence for `PASS`.

## Assessment discipline

Please preserve these invariants:

- no aggregate scores, rankings or star ratings;
- no transitive credit between A–G;
- absence of evidence means `UNTESTED`, not `FAIL`;
- explicit non-claims mean `OUT_OF_SCOPE`, not `FAIL`;
- partial passes must name both supported scope and untested remainder;
- disagreements with implementers should be recorded, not silently rewritten.

## Proposing a new property

A new property proposal should answer four questions:

1. What independent authority or execution question is missing?
2. Why can it not be represented by the existing A–G properties?
3. What concrete test distinguishes it from its nearest existing property?
4. What inference must evidence for the new property **not** permit?

## Pull requests

Keep changes narrow and evidence-linked. Prefer one conceptual change per pull request. If a change alters a normative property boundary, include an example or fixture that demonstrates the reason.

The goal is not to make more systems pass. The goal is to make every result easier to interpret and harder to overstate.
