# AgentAvow MCP tool-definition binding v1 — REMORA-side consumer

This directory records a Python implementation of the derivation published by AgentAvow for the federation E1 edge. It intentionally imports no AgentAvow or APS implementation code.

## Pin

- Producer: `AgentAvow/AgentAvow`
- Commit: `36426cfd5152bba6a27766febfac8aaef47b6f34`
- Upstream vector path: `docs/standards/tool-manifest-digest-vectors-v1/tool-manifest-digest-v1-vectors.json`
- Local fixture: `interop/fixtures/agentavow-tool-manifest-digest-v1.json`

Run:

```bash
python -m unittest tests.test_agentavow_tool_binding -v
```

## Claim ceiling

A passing run independently reproduces the published tool-key derivation, per-tool definition digests, Ed25519/JWS verification, subject binding, validity window, and six gate outcomes.

| Claim | Status after a passing run |
|---|---|
| observed MCP tool definition bound to signed per-tool digest | ESTABLISHED for pinned fixture |
| signed subject/tool/freshness gate semantics reproduce | ESTABLISHED for pinned fixture |
| runtime capability-surface completeness | NOT_ESTABLISHED |
| semantic authority for an invocation | NOT_ESTABLISHED |
| execution authorization | NOT_ESTABLISHED |
| runtime behavior of the tool | NOT_ESTABLISHED |
| effect occurrence / effect correctness | NOT_ESTABLISHED |

This edge supplies source/tool-definition evidence that a REMORA authority or execution gate may consume. It does not upgrade discovery or a static scan into authority, execution evidence, or effect verification.
