# Roadmap

## Shipped

The offline deterministic core: envelope models, promotion rules, safe
bounded loading, JSON/HTTP/MCP/stdio/YAML adapters, the CLI, deterministic
reports, the `check` / `seal` Python API, a fixture corpus drawn from real
backends, and tested examples for seven agent frameworks.

## Next, only with user evidence

Possible follow-up work includes more adapters, a plugin protocol, optional
cryptographic evidence references, and integrations with existing test
frameworks. None of these are added until users ask for them with a concrete
failure they hit.

A 1.0 release will freeze the Python API alongside the already-stable
contract schema, reason codes, and CLI exit codes once the API has had real
users.

## Forbidden expansion

Do not expand into a hosted service, general agent runtime, dashboard, policy
engine, transaction manager, or universal evaluator.
