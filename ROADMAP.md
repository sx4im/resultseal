# Roadmap

## Shipped

The offline deterministic core: envelope models, promotion rules, safe
bounded loading, JSON/HTTP/MCP/stdio/YAML adapters, the CLI, deterministic
reports, the `check` / `seal` Python API, a fixture corpus drawn from real
backends, tested examples for seven agent frameworks, and a
[Claude Code and Codex plugin](https://github.com/sx4im/resultseal/tree/master/plugins/resultseal)
whose hook seals MCP tool results against per-tool contracts.

## Next, only with user evidence

Possible follow-up work includes more adapters, a plugin API for registering
third-party adapters (separate from the agent plugin above), optional
cryptographic evidence references, and integrations with existing test
frameworks. None of these are added until users ask for them with a concrete
failure they hit.

A 1.0 release will freeze the Python API alongside the already-stable
contract schema, reason codes, and CLI exit codes once the API has had real
users.

## Forbidden expansion

Do not expand into a hosted service, general agent runtime, dashboard, policy
engine, transaction manager, or universal evaluator.
