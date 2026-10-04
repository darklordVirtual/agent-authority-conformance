# Terminology

## Names

| Name | Role |
|---|---|
| REMORA | an assured-agent-execution implementation; one implementation under test here |
| AACP, Agent Authority Conformance Profiles | this project: portable, implementation-neutral conformance profiles and falsification fixtures |
| BCR, Bounded Claim Reproduction | the evidence method: what was tested, by whom, against which revisions, and what the result does and does not establish |
| Agent Authority Conformance (LF Decentralized Trust lab) | an external, neutral conformance venue with Agent Passport System as its first corpus; not this project |
| Federation | cooperation and interoperability between sovereign projects; one consumer of AACP results among others |

This project was published as "Agent Authority Conformance" until 2026-10.
The name was given up because it is the name of the LF Decentralized Trust
lab. Records written under the old name, including the v0.1 and v0.2
specifications and the committed assessments, keep their text. The v0.1
specification and schema are byte-pinned by a test and keep the former name
and `$id` verbatim.

## Four different things

| Term | Statement it supports |
|---|---|
| Conformance | implementation X satisfies profile P under run R |
| Interoperability | implementation X produces something implementation Y can consume under a specified boundary contract |
| Validation | evidence supports a particular technical claim |
| Certification | an authorized organization declares that defined certification requirements are met |

AACP produces conformance evidence. BCR produces reproduction evidence.
Federation uses both for interoperability. An implementation may cite them as
validation evidence for its own claims. None of them is certification, and
none may be presented as one.

## The seven properties

The A to G property model of the v0.1 and v0.2 specifications is unchanged.

| ID | Property | Core question |
|---|---|---|
| A | Receipt Integrity | Is the authorization artifact authentic, unmodified, valid and correctly replay-bounded? |
| B | Authority Provenance | Can the system establish who or what had authority to approve the action? |
| C | Exact-Call Integrity | Is authorization bound to the exact tool call that is executed? |
| D | Semantic Authority | Was the action permitted in its real operational meaning? |
| E | Execution-Boundary Integrity | Can the protected effect be reached only through the governed path? |
| F | TOCTOU Resistance | Can approved conditions change between authorization and execution? |
| G | Effect Verification | Does the system verify the actual external effect after execution? |

Evidence for one property grants no credit in another.

## Profile identity

A profile has a stable identifier of the form `AACP-<PROPERTY-NAME>-<revision>`,
for example `AACP-EXACT-CALL-BINDING-1`. A revision is frozen once published:
later fixtures go into a new revision, so "conformant to revision 1" keeps
meaning what it meant when the result was recorded.

Every profile contains six things: the normative claim, the input contract,
positive fixtures, negative and mutation fixtures, the evaluation procedure,
and the claim ceiling.
