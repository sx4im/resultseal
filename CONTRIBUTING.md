# Contributing to ResultSeal

ResultSeal is a deterministic, fail-closed boundary that stops AI agents from
promoting unverified tool results into factual claims. Contributions that
make that boundary sharper or easier to adopt are welcome.

## Finding something to work on

- [Good first issues](https://github.com/sx4im/resultseal/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22):
  well-scoped tasks with reference files and expected outcomes.
- [Help wanted](https://github.com/sx4im/resultseal/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22):
  adapters, integrations, and fixtures.

Comment on an issue to claim it before starting, so two people do not build
the same thing.

## Development setup

```bash
git clone https://github.com/sx4im/resultseal.git
cd resultseal
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
make all   # pytest, ruff, mypy --strict, build
```

`tests/test_playground.py` checks the GitHub Pages playground against the
engine and needs Node.js on `PATH`; without Node it is skipped locally, but
CI always runs it.

## Where contributions help most

1. **Fixtures from real backends.** Capture what a real API, database, MCP
   server, or CLI returns when nothing matched or something half-failed, and
   add it to `fixtures/` with its contract and expected outcome. The fixture
   matrix test and `resultseal replay` pick it up automatically; add a row to
   [FIXTURE_CATALOG.md](docs/specs/FIXTURE_CATALOG.md).
2. **Framework examples.** Seven frameworks are covered. Others (OpenAI
   Agents SDK, Semantic Kernel, Haystack, DSPy, ...) should follow the
   existing files: delegate to `resultseal.seal`, keep framework imports
   inside a factory function so the module imports without them, add
   `runpy`-based tests to `tests/test_examples.py`, and run the example
   against the real framework before opening the PR.
3. **Adapters.** An adapter establishes structural facts only, never
   semantic success. Read [ADAPTERS.md](docs/specs/ADAPTERS.md) first.
4. **Contract recipes.** Production contract patterns for common APIs
   (GitHub, Stripe, AWS, Slack).

## Principles

- **Fail closed.** When evidence is missing, ambiguous, or malformed, the
  answer is blocked or rejected, never sealed.
- **Pure rules.** `rules.py`, `models.py`, and `canonical.py` do no I/O, read
  no environment or wall clock, and execute nothing from their inputs.
  `tests/test_purity.py` enforces this.
- **Determinism.** Replaying a fixture with a pinned reference clock must
  produce byte-identical JSON and the same SHA-256 fingerprint.
- **Evidence.** Every behavior change or bug fix ships with a regression
  test or fixture that fails without it.
- **Decision log.** If a change touches a documented invariant (a promotion
  rule, reason code, schema field, or adapter contract), add a dated
  `## D<number> — <date> — <title>` entry to
  [docs/decision-log.md](docs/decision-log.md).
- **Docs are tested.** Python blocks in the README are executed by
  `tests/test_readme.py`; keep them runnable.

Before opening a pull request, run the same gates as CI:

```bash
ruff check .
mypy src
pytest
```
