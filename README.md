# ResultSeal

**HTTP 200 is not an observation. Empty is not not-found. A tool call is not an effect.**

ResultSeal is a small, framework-neutral Python toolkit that prevents AI-agent workflows from promoting empty, partial, stale, source-mismatched, or unverified tool results into factual claims.

## What it does

ResultSeal normalizes a tool result, applies a declarative contract, and produces a deterministic decision. Unknown and incomplete evidence is blocked by default.

```bash
pip install resultseal
resultseal replay fixtures/empty-result.yaml
resultseal replay fixtures/explicit-not-found.yaml
```

The first command shows why an empty response cannot become `not_found`. The second shows how an explicit contract-approved not-found sentinel can seal safely.

## Scope

ResultSeal is not an agent framework, proxy, dashboard, policy engine, retry middleware, signed receipt system, or LLM judge. It is an executable semantic boundary for tool observations.

## Development

```bash
make install   # editable install with dev tools
make all       # test, lint, typecheck, build
```

Requires Python 3.11+.
