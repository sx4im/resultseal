# ResultSeal

[![CI](https://github.com/sx4im/resultseal/actions/workflows/ci.yml/badge.svg)](https://github.com/sx4im/resultseal/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)

**HTTP 200 is not an observation. Empty is not not-found. A tool call is not an effect.**

ResultSeal is a small, framework-neutral Python toolkit that prevents AI-agent workflows from promoting empty, partial, stale, source-mismatched, or unverified tool results into factual claims. Shipped adapters cover raw JSON, HTTP responses, MCP-style tool results (`structuredContent` / `isError` / `outputSchema`), and stdio process output — each establishing structural facts only (see [docs/specs/ADAPTERS.md](docs/specs/ADAPTERS.md)).

## What it does

ResultSeal normalizes a tool result, applies a declarative contract, and produces a deterministic decision. Unknown and incomplete evidence is blocked by default.

## Install

```bash
pip install resultseal
```

Requires Python 3.11+.

From source instead:

```bash
git clone https://github.com/sx4im/resultseal.git
cd resultseal
pip install .
```

## Try it

```bash
# Replay a self-contained fixture bundle against its recorded expectation
resultseal replay fixtures/empty-result.yaml         # empty response -> blocked/empty
resultseal replay fixtures/explicit-not-found.yaml   # approved sentinel -> sealed/not_found

# Evaluate a shipped example against a shipped contract (exit 0 = sealed, 1 = blocked)
resultseal check examples/mcp_result.json --contract examples/customer_contract.json
resultseal check examples/http_empty.json --contract examples/customer_contract.json
```

The last two are the toolkit's thesis side by side: a complete MCP result seals,
while an HTTP 200 carrying an empty body blocks as `empty` — it can never be
promoted to `not_found`. All four commands print the decision record with a
verifiable `deterministic_fingerprint`.

## Scope

ResultSeal is not an agent framework, proxy, dashboard, policy engine, retry middleware, signed receipt system, or LLM judge. It is an executable semantic boundary for tool observations.

## Development

```bash
make install   # editable install with dev tools
make all       # test, lint, typecheck, build
```

## Contributing

Bug reports, fixes, and spec feedback are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for what a change is expected to include. The normative specifications live in [docs/specs/](docs/specs/), and changes that touch a documented invariant add a dated entry to the [decision log](docs/decision-log.md).
