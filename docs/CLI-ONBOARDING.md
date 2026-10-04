# CLI onboarding

The installer name is `aacp-conformance`; the command is `aacp`. This is the
first CLI slice: project onboarding, strict configuration validation and local
Git pin inspection. It does not run a property verifier or discover evidence.

## Install and start

Python 3.12 or newer, from an AACP checkout:

```sh
pipx install .
cd /path/to/your-project
aacp init --name example-agent --role producer --role consumer
aacp validate --json
aacp inspect --json
```

Without pipx, install into a virtual environment with `python -m pip install .`.
For development, `python -m aacp` provides the same interface from the checkout.
No PyPI release is implied: `pipx install aacp-conformance` becomes available
only after an explicitly authorized package publication. The distribution
includes the committed JSON schemas; no AACP checkout is needed at runtime.
The existing `python -m conformance.*` developer tools remain separate and
require the repository and its committed corpus.

## Project contract

`aacp init` writes `aacp-project.yaml` in the current directory. It refuses to
overwrite an existing file. It does not modify project source, execute subject
code, contact a network service or read remote credentials. Use `--project PATH`
to select a different file; its parent directory must already exist.

```yaml
schema_version: aacp-project-v1
project:
  name: example-agent
  repository: UNKNOWN
  revision: AUTO
roles:
  - producer
  - consumer
surfaces:
  - id: signed-tool-manifest
    role: producer
    contract: tool-manifest-v1
  - id: authority-gateway
    role: consumer
    consumes: tool-manifest-v1
claims:
  discovery: assisted
execution:
  external_code: deny_by_default
  network: deny_by_default
review:
  publication: PRIVATE_UNTIL_APPROVED
```

The schema is
[aacp-project-v1.schema.json](../schema/aacp-project-v1.schema.json).
Roles are `producer`, `consumer`, `verifier` and `reproduction`. Interop is an
edge between roles, not a fifth role or an inferred property of one project.
Consumer surfaces name the contract they consume; producer surfaces name the
contract they produce. Surface IDs must be unique and their roles must be
declared at project level. Declared contracts are labels, not proof of support.

Use `UNKNOWN` for missing repository/revision facts. `AUTO` asks inspection to
read local Git HEAD without freezing or rewriting the configuration. A known
HEAD does not bind working-tree contents or authenticate artifact bytes. Replace
`AUTO` with an agreed full 40-character revision before an evaluative run.
An explicit pin differing from local HEAD appears as `MISMATCH`, not `FAIL`.
Repositories use a declared HTTPS URL, never a token or secret.

Unknown keys, non-string mapping keys, duplicate YAML keys, aliases, arbitrary
YAML constructors, nesting beyond 64 levels, unsupported versions and files
larger than 1 MiB are rejected.
This initial contract accepts only deny-by-default execution/network policy.
There is no subject-execution opt-in flag in this release. Review policy is a
declaration, not a publication grant; none of these commands publish anything.

## Human and machine results

Each command accepts `--json`, before or after the subcommand. Machine output
is one JSON document on stdout, including invalid-input and filesystem errors.
Human output is a readable summary of the same non-verdict data. `--help` is
normal CLI help text rather than a workflow record.

The envelope validates against
[aacp-command-result-v1.schema.json](../schema/aacp-command-result-v1.schema.json):

- `status`: command/configuration `OK`, `INVALID_INPUT` or `ERROR`;
- `verification_status`: always `NOT_RUN` for onboarding;
- `property_verdict`: always `null`;
- `data`: declared project, raw configuration SHA-256 and local pin metadata
  where applicable;
- `errors`: typed non-verdict errors;
- `next_action`: the next bounded onboarding step and its output schema;
- `claim_ceiling`: explicit configuration-only scope.

Exit 0 means the command completed; exit 2 means invalid or missing input;
exit 3 means a local I/O/tooling error. `inspect` reads only configuration and
local Git HEAD using `git rev-parse`; it does not invoke project tests, hooks,
filters, adapters, network fetches or verifier plugins. A missing Git repository
leaves the pin `UNKNOWN`. A missing Git executable is a tooling error.

`assisted` permits future candidate suggestions; it does not turn AI prose into
evidence. Configuration validation is not resolution, resolution is not
admission, and admission is not an established property. No score is computed.

## Next slices

The planned `profiles`, `doctor`, `plan`, `next`, `collect`, `verify`, `interop`,
`mutate`, `reproduce`, `report` and `ai-context` commands are **not implemented**
by this onboarding release. They must be added with their own typed contracts,
applicability rules, evidence boundaries and negative controls, not placeholder
success responses. Profile registry, consumer/verifier contracts and BCR run
schemas precede an executable assessment workflow. PyPI, reusable Actions and
container publication are separate, explicitly authorized distribution tasks.