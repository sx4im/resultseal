# Contributing to ResultSeal

Thank you for your interest in contributing! ResultSeal is an evidence-driven, deterministic toolkit that prevents AI agents from promoting unverified tool observations into factual claims.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/sx4im/resultseal.git
cd resultseal

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install editable package with development dependencies
pip install -e ".[dev]"

# Run verification suite (pytest, ruff, mypy, build)
make all
```

## Where We Welcome Contributions

We actively welcome contributions in the following areas:

1. **New Adapters & Protocol Normalizers**: Adapters for SQL query outputs, GraphQL responses, or specific tool protocols. (Remember: an adapter establishes structural facts only, never semantic success).
2. **Negative Test Fixtures**: Real-world failure cases and edge cases from MCP servers, APIs, or subprocesses added to `fixtures/`.
3. **Framework Integrations**: Examples and integration helpers for popular agent frameworks (LangChain, LangGraph, Pydantic-AI, CrewAI, AutoGen, Smolagents).
4. **Documentation & Real-World Recipes**: Production contract patterns for standard APIs (GitHub, Stripe, AWS, Slack).

## Contribution Principles

- **Fail-closed & Pure**: Promotion rules must remain pure functions (no network calls, no subprocesses, no unpinned wall clocks, no dynamic code execution).
- **Determinism**: Replaying a fixture with an identical reference clock must produce byte-identical JSON and matching SHA-256 fingerprints.
- **Evidence-driven**: Include regression tests or negative-test fixtures (`.yaml`) for every new behavior or bugfix.
- **Decision Log**: If your change touches a documented invariant (a promotion rule, error code, schema field, or adapter contract), add a dated entry `## D<number> — <date> — <title>` to [docs/decision-log.md](docs/decision-log.md).

Before opening a pull request, ensure all gates pass:
```bash
ruff check .
mypy src
pytest
```


