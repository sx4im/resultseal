# ResultSeal

[![CI](https://github.com/sx4im/resultseal/actions/workflows/ci.yml/badge.svg)](https://github.com/sx4im/resultseal/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/resultseal.svg)](https://pypi.org/project/resultseal/)
[![Demo](https://img.shields.io/badge/Playground-Live%20Demo-blue.svg)](https://sx4im.github.io/resultseal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)

**HTTP 200 is not an observation. Empty is not not-found. A tool call is not an effect.**

ResultSeal is a small, framework-neutral Python toolkit that prevents AI-agent workflows from promoting empty, partial, stale, source-mismatched, or unverified tool results into factual claims. Shipped adapters cover raw JSON, HTTP responses, MCP-style tool results (`structuredContent` / `isError` / `outputSchema`), and stdio process output — each establishing structural facts only (see [docs/specs/ADAPTERS.md](docs/specs/ADAPTERS.md)).

```
  ┌─────────────────┐       ┌──────────────┐       ┌──────────────────────┐
  │ Raw Tool Output │ ───>  │  ResultSeal  │ ───>  │ SEALED  ─> Agent OK  │
  │ (HTTP/MCP/JSON) │       │   Contract   │       │ BLOCKED ─> Halt/Err  │
  └─────────────────┘       └──────────────┘       └──────────────────────┘
```

## Why ResultSeal

AI agents frequently suffer from false-success hallucinations: treating empty search responses as proof of absence, or transport-level HTTP 200s as verified effects. Standard schema validators only verify payload shape—ResultSeal enforces observation integrity:

| Tool Output Scenario | Naive Agent Behavior | ResultSeal Guard |
|---|---|---|
| **Query returns `{}` or `[]`** | Hallucinates: *"Item does not exist"* | **`BLOCKED`** (`EMPTY_WITHOUT_NOT_FOUND_SENTINEL`) |
| **Explicit absence (`{"status": "NOT_FOUND"}`)** | May confuse with unexpected error | **`SEALED`** (`not_found` via contract sentinel) |
| **HTTP 204 DELETE (empty body)** | Assumes mutation succeeded without proof | **`BLOCKED`** (`UNVERIFIED_EFFECT`) |
| **MCP returns `isError: true` with text** | Reads error message as answer | **`BLOCKED`** (`PROTOCOL_CONFLICT`) |
| **Cache returns outdated revision** | Acts on stale state | **`BLOCKED`** (`STALE_OBSERVATION`) |
| **Missing required fields** | Promotes partial payload | **`BLOCKED`** (`MISSING_REQUIRED_FIELD`) |

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

### CLI

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

### Python API

```python
import json
from datetime import datetime, UTC
from pathlib import Path
from resultseal.contracts import load_contract_file
from resultseal.limits import Limits
from resultseal.models import Decision
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock, evaluate

# 1. Load a declarative contract
contract = load_contract_file(Path("examples/customer_contract.json"), Limits())

# 2. Normalize raw tool observation (MCP, HTTP, stdio, or JSON)
raw_tool_result = json.loads(Path("examples/mcp_result.json").read_text())
clock = ReferenceClock(now=datetime.now(UTC))
norm = normalize(raw_tool_result, clock)

# 3. Evaluate observation against contract
evaluation = evaluate(norm.envelope, norm.payload, contract, clock)

if evaluation.decision is Decision.SEALED:
    print(f"Observation verified! Truth state: {evaluation.truth_state.value}")
else:
    print(f"Blocked! Reason codes: {evaluation.reason_codes}")
```

## Scope

ResultSeal is not an agent framework, proxy, dashboard, policy engine, retry middleware, signed receipt system, or LLM judge. It is an executable semantic boundary for tool observations.

## Development

```bash
make install   # editable install with dev tools
make all       # test, lint, typecheck, build
```

## Contributing

Contributions are warmly welcome! Whether you are:
- Adding a new protocol adapter (e.g. SQL query results, GraphQL)
- Submitting an edge-case negative test fixture in `fixtures/`
- Contributing an integration example for an agent framework (LangChain, LangGraph, Pydantic-AI, CrewAI)
- Improving documentation or adding production contract recipes

Check out [CONTRIBUTING.md](CONTRIBUTING.md) to get set up in under two minutes.

## Contributors

Thanks to the contributors who have improved ResultSeal:

<a href="https://github.com/sx4im/resultseal/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sx4im/resultseal" alt="Contributors" />
</a>


