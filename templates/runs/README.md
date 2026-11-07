# Run skeletons

Each directory holds a `SCOPE.json` and the run-owned material next to it (`verifier/`,
and for adequacy runs `faults/`, `controls/`, `adapter/`). `init --template
templates/runs/<name>/SCOPE.json` copies both into `runs/<run_id>`; `pin` then records the
SHA-256 of every subject file.

| Skeleton | Kind | Basis | What it answers |
|---|---|---|---|
| [`nti-witness/`](nti-witness/) | verification, bytes inputs, probes | public boundary, two revisions of one repository | The NTI witness-package challenge in aeoess/agent-governance-vocabulary#177. See [docs/CHALLENGE-RESPONSE.md](../../docs/CHALLENGE-RESPONSE.md). |

A skeleton is not an agreed scope and not a result. Results live only in the run
directory and its package.
