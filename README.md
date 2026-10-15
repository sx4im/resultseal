<p align="center">
  <img src="https://raw.githubusercontent.com/sx4im/resultseal/master/assets/logo.png" width="120" height="120" alt="ResultSeal logo" />
</p>

<h1 align="center">ResultSeal</h1>

<p align="center">
  <b>HTTP 200 is not an observation. Empty is not not-found. A tool call is not an effect.</b>
</p>

<p align="center">
  <a href="https://github.com/sx4im/resultseal/actions/workflows/ci.yml"><img src="https://github.com/sx4im/resultseal/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://pypi.org/project/resultseal/"><img src="https://img.shields.io/pypi/v/resultseal.svg" alt="PyPI" /></a>
  <a href="https://pypi.org/project/resultseal/"><img src="https://img.shields.io/pypi/pyversions/resultseal.svg" alt="Python versions" /></a>
  <a href="https://github.com/sx4im/resultseal/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="MIT license" /></a>
  <a href="https://sx4im.github.io/resultseal/"><img src="https://img.shields.io/badge/playground-live-blue.svg" alt="Live playground" /></a>
</p>

An agent asks a CRM tool for customer 42. The search returns `[]`, and the
agent tells the user the customer does not exist. Nothing failed: the HTTP
status was 200, the JSON was valid, the schema check passed. The empty list
simply got promoted into a fact it never supported.

ResultSeal sits between your tools and your model. You declare, per tool,
what a result has to contain before it may back a claim. ResultSeal checks
each raw result against that contract and either **seals** it or **blocks**
it with a stable reason code. Empty, partial, stale, mismatched, errored and
unverified results are blocked by default.

- **Framework-neutral.** Plain Python and a CLI. There are drop-in examples
  for LangChain, LangGraph, LlamaIndex, CrewAI, Pydantic-AI, smolagents and
  AutoGen.
- **Deterministic.** The same input and reference clock always produce the
  same decision and the same SHA-256 fingerprint. No model calls and no
  network.
- **Small and strict.** One runtime dependency (PyYAML). Inputs are bounded,
  YAML tags and anchors are refused, and contracts are data only.

## What it catches

| The tool returns | A naive agent concludes | ResultSeal |
|---|---|---|
| `[]` or `{}` from a search | "That record does not exist." | blocked: `EMPTY_WITHOUT_NOT_FOUND_SENTINEL` |
| `{"status": "NOT_FOUND"}`, and the contract names `NOT_FOUND` as its sentinel | "That record does not exist." This time it is right. | sealed: `not_found` |
| HTTP 404 with `{"error": "not_found"}` | "Confirmed absent." | blocked: `TRANSPORT_FAILED` |
| HTTP 204 with an empty body after a `DELETE` | "Deleted." | blocked: `EMPTY_WITHOUT_NOT_FOUND_SENTINEL` |
| MCP result with `isError: true` and some text | Reads the error text as the answer | blocked: `PROTOCOL_CONFLICT` |
| A cached record at `revision-9` when the contract needs `revision-12` | Acts on stale state | blocked: `STALE_OBSERVATION` |
| `{"customer_id": "42"}` when `name` is required | Fills the gap | blocked: `MISSING_REQUIRED_FIELD` |
| A record for `customer:7` when you asked for `customer:42` | Answers about the wrong customer | blocked: `TARGET_MISMATCH` |
| "Email sent" with no message id | "Done." | blocked: `UNVERIFIED_EFFECT` |

Several of these cases are presets in the [playground](https://sx4im.github.io/resultseal/).

## Install

```bash
pip install resultseal
```

Requires Python 3.11 or newer.

## Quickstart

### Guard a tool in Python

A contract says what a sealed result must contain and where it must come
from:

```python
import resultseal

contract = resultseal.load_contract({
    "schema_version": "1",
    "claim_type": "found",
    "required_fields": ["customer_id", "name"],
    "freshness": {"mode": "not_required"},
    "source_ref": "crm://customers",
    "target_ref": "customer:42",
})
```

Wrap the raw tool output in an adapter input and call `seal`. It returns the
payload when the result is sealed and raises `BlockedObservation` when it is
not, so a blocked result cannot reach the model through a forgotten `if`:

```python
def observe(rows):
    return {
        "kind": "json",
        "source_ref": "crm://customers",
        "target_ref": "customer:42",
        "tool_name": "search_customer",
        "body": rows,
    }

resultseal.seal(observe({"customer_id": "42", "name": "Ada"}), contract)
# -> {'customer_id': '42', 'name': 'Ada'}

try:
    resultseal.seal(observe([]), contract)
except resultseal.BlockedObservation as blocked:
    print(blocked)
    # observation blocked as empty: EMPTY_WITHOUT_NOT_FOUND_SENTINEL
```

smolagents and AutoGen hand a tool's exception back to the model as an
error result, as does LangGraph's `ToolNode(handle_tool_errors=True)`. The
model then reads "observation blocked as empty" where it would otherwise
have read `[]`.

If you want to branch on the result instead of catching an exception, use
`check`. `record()` returns the decision record, the same JSON that the CLI
prints:

```python
result = resultseal.check(observe({"customer_id": "42"}), contract)

result.sealed        # -> False
result.truth_state   # -> TruthState.PARTIAL
result.reason_codes  # -> ('MISSING_REQUIRED_FIELD',)
result.record()["deterministic_fingerprint"]  # 'sha256:' + 64 hex digits
```

Absence can be sealed too, but only when the source says so explicitly. A
`not_found` contract names the sentinel value that counts as a real
"no such record":

```python
not_found = resultseal.load_contract({
    "schema_version": "1",
    "claim_type": "not_found",
    "required_fields": [],
    "freshness": {"mode": "not_required"},
    "source_ref": "crm://customers",
    "target_ref": "customer:42",
    "not_found_sentinel": "NOT_FOUND",
})

resultseal.check(observe({"status": "NOT_FOUND"}), not_found).sealed  # -> True
resultseal.check(observe([]), not_found).sealed                       # -> False
```

### Check from the command line

The CLI evaluates JSON or YAML files and uses exit codes, so it fits into CI:

```bash
# A complete MCP result seals (exit 0)
resultseal check examples/mcp_result.json --contract examples/customer_contract.json

# An HTTP 200 with an empty body blocks (exit 1)
resultseal check examples/http_empty.json --contract examples/customer_contract.json --format md

# Replay every shipped fixture against its recorded expectation
resultseal replay fixtures/*.yaml

# Validate a contract or fixture without evaluating anything
resultseal validate examples/customer_contract.json
```

```text
MATCH: bare-json-payload -> empty/blocked
MATCH: complete-fresh-result -> sealed/sealed
MATCH: dynamodb-empty-query -> partial/blocked
...
MATCH: unsafe-input -> rejected (UNSAFE_INPUT)
```

| Exit code | `check` | `replay` | `validate` |
|---|---|---|---|
| 0 | sealed | every expectation matched | valid |
| 1 | blocked | at least one mismatch | — |
| 2 | invalid input or contract | invalid fixture | invalid |
| 3 | unsafe input (limits, YAML tags or anchors) | unsafe fixture document | unsafe |

`check` and `replay` accept `--format json|md`, `--now <ISO-8601>` to pin the
reference clock, and `--redact FIELD` (repeatable) to mask record fields
before they are fingerprinted.

## Framework integrations

Each example is a single self-contained file. The guard runs without the
framework installed, so the test suite covers every example. Each example
was also run end to end against current releases of its framework.

| Framework | Example | Hook point |
|---|---|---|
| LangChain | [`langchain_tool_guard.py`](https://github.com/sx4im/resultseal/blob/master/examples/langchain_tool_guard.py) | `@tool` |
| LangGraph | [`langgraph_tool_guard.py`](https://github.com/sx4im/resultseal/blob/master/examples/langgraph_tool_guard.py) | `ToolNode` inside a `StateGraph` |
| LlamaIndex | [`llamaindex_tool_guard.py`](https://github.com/sx4im/resultseal/blob/master/examples/llamaindex_tool_guard.py) | `FunctionTool` |
| CrewAI | [`crewai_tool_guard.py`](https://github.com/sx4im/resultseal/blob/master/examples/crewai_tool_guard.py) | `crewai.tools.tool` |
| Pydantic-AI | [`pydantic_ai_guard.py`](https://github.com/sx4im/resultseal/blob/master/examples/pydantic_ai_guard.py) | `@agent.tool_plain`, run offline with `TestModel` |
| smolagents | [`smolagents_tool_guard.py`](https://github.com/sx4im/resultseal/blob/master/examples/smolagents_tool_guard.py) | `@tool` |
| AutoGen | [`autogen_tool_guard.py`](https://github.com/sx4im/resultseal/blob/master/examples/autogen_tool_guard.py) | `AssistantAgent` tools, run offline with `ReplayChatCompletionClient` |

All of them follow the same pattern:

```python
from pathlib import Path

import resultseal

CONTRACT = resultseal.load_contract(Path("examples/customer_contract.json"))

def search_customer(query: str) -> object:
    rows = []  # your real lookup goes here
    return resultseal.seal(
        {"kind": "json", "source_ref": "mcp://crm-server",
         "target_ref": "customer:42", "body": rows},
        CONTRACT,
    )
```

## How it decides

### Adapter inputs

An input is a JSON object that describes one tool result. Every input needs a
`source_ref` and a `target_ref`. These are the identity that the contract
must match. Inputs may also carry `tool_name`, `observed_at`,
`source_version`, `evidence_refs`, `observation_id`, `tool_call_id` and
scalar `metadata`. If you leave out `kind`, it is inferred from the fields
that are present.

| `kind` | Payload fields | Structural facts it establishes |
|---|---|---|
| `json` | `body` (structured value, or a JSON string) | Only `body` is the payload. Other top-level fields are metadata. |
| `http_json` | `status_code`, `body` | 2xx/3xx means transported. Any other status is `TRANSPORT_FAILED`, whatever the body says. |
| `mcp` | `structuredContent`, `text`, `isError`, `outputSchema` | `isError: true` is a `PROTOCOL_CONFLICT`. `structuredContent` takes precedence over `text`. |
| `stdio` | `exit_code`, `stdout`, `output_format: json` | A non-zero exit is `TRANSPORT_FAILED`. A zero exit proves only that the process completed. |
| `yaml` | `value` (YAML text) | Parsed under the same safe loader as files. |
| `claim_only` | `claim` | A claim with no dispatch record. It is always `NO_DISPATCH`. |

### Contracts

| Field | Meaning |
|---|---|
| `schema_version` | Always `"1"`. |
| `claim_type` | `found`, `not_found`, `read_complete`, `effect_observed` or `task_complete`. |
| `required_fields` | Top-level payload keys that must be present. |
| `freshness` | `{"mode": "not_required"}`, `{"mode": "source_version"}` (needs `min_source_version`), or `{"mode": "max_age_seconds", "max_age_seconds": N}`. |
| `source_ref`, `target_ref` | The identity the observation must carry. |
| `not_found_sentinel` | The only value that can seal a `not_found` claim. |
| `effect_evidence_required` | For effect and task claims, require non-empty `evidence_refs`. |

### Evaluation order

The rules run in a fixed order and the first one that fails decides the
result. The engine is a pure function: it does no I/O and reads no clock or
environment.

| # | Condition | Truth state | Reason code |
|---|---|---|---|
| 1 | No dispatch record | `unknown` | `NO_DISPATCH` |
| 2 | Transport failed | `unknown` | `TRANSPORT_FAILED` |
| 3 | Payload did not parse | `parse_error` | `PARSE_FAILED` |
| 4 | Protocol contradicts itself | `unknown` | `PROTOCOL_CONFLICT` |
| 5 | Payload is empty and the sentinel does not match | `empty` | `EMPTY_WITHOUT_NOT_FOUND_SENTINEL` |
| 6 | Source or target differs from the contract | `source_mismatch` | `SOURCE_MISMATCH`, `TARGET_MISMATCH` |
| 7 | Older than the freshness requirement | `stale` | `STALE_OBSERVATION` |
| 8 | Required field missing | `partial` | `MISSING_REQUIRED_FIELD` |
| 9 | Effect claimed without evidence | `unverified_effect` | `UNVERIFIED_EFFECT` |
| 10 | Every condition holds | `sealed` (`not_found` for absence) | `SEALED_WITH_REQUIRED_EVIDENCE` |

Malformed or unsafe input is never evaluated. It raises a `ResultSealError`
whose code is one of `SCHEMA_INVALID`, `PARSE_FAILED`, `CONTRACT_INVALID`,
`INVALID_ARGUMENT`, `UNSAFE_INPUT` or `LIMIT_EXCEEDED`. The full precedence
rules are in [PROMOTION_RULES.md](https://github.com/sx4im/resultseal/blob/master/docs/specs/PROMOTION_RULES.md).

## Fixtures from real backends

[`fixtures/`](https://github.com/sx4im/resultseal/tree/master/fixtures/) holds 19 self-contained cases. Each one includes the
input, the contract and the expected outcome. Every CI run replays all of
them. They cover the core semantics and the response shapes that real
backends produce when nothing matched: SQL empty result sets, Redis `nil`,
Elasticsearch zero hits, DynamoDB `Items: []`, GraphQL `data: null` with
errors, and structured HTTP 404 bodies. The
[fixture catalog](https://github.com/sx4im/resultseal/blob/master/docs/specs/FIXTURE_CATALOG.md) lists each case and why it
seals or blocks.

## Guarantees and limits

- **Determinism.** Decisions depend only on the input, the contract and the
  reference clock. Reports never contain wall-clock values. Pin `--now` (or
  `now=`) if you need `max_age_seconds` verdicts that replay identically.
- **Bounded input.** By default: 128 KiB per file, nesting depth 32, 4,096
  nodes, 16,384-character strings. These are checked before and right after
  parsing. YAML anchors, aliases, and any tag beyond the plain scalar,
  sequence, mapping, and timestamp types are refused.
- **Offline.** The package never opens a socket or starts a subprocess. A
  test scans the source to enforce this.
- **Scope.** ResultSeal protects the local promotion decision. It does not
  prove that a remote system is honest, judge the quality of a model's prose,
  or replace authorization. See [THREAT_MODEL.md](https://github.com/sx4im/resultseal/blob/master/docs/specs/THREAT_MODEL.md)
  and [NON_GOALS.md](https://github.com/sx4im/resultseal/blob/master/docs/specs/NON_GOALS.md).

ResultSeal is not an agent framework, proxy, dashboard, policy engine, retry
layer or LLM judge. It is one function you call at the tool boundary.

## Documentation

- [Architecture](https://github.com/sx4im/resultseal/blob/master/docs/specs/ARCHITECTURE.md): modules and data flow
- [Adapters](https://github.com/sx4im/resultseal/blob/master/docs/specs/ADAPTERS.md): what each adapter may and may not conclude
- [Promotion rules](https://github.com/sx4im/resultseal/blob/master/docs/specs/PROMOTION_RULES.md) and [error codes](https://github.com/sx4im/resultseal/blob/master/docs/specs/ERROR_CODES.md)
- [CLI contract](https://github.com/sx4im/resultseal/blob/master/docs/specs/CLI_CONTRACT.md) and [report format](https://github.com/sx4im/resultseal/blob/master/docs/specs/REPORT_FORMAT.md)
- [Decision log](https://github.com/sx4im/resultseal/blob/master/docs/decision-log.md): every semantic decision, with dates and reasons
- [Changelog](https://github.com/sx4im/resultseal/blob/master/CHANGELOG.md)

## Contributing

New fixtures from real backends, framework examples and adapter work are all
welcome. [CONTRIBUTING.md](https://github.com/sx4im/resultseal/blob/master/CONTRIBUTING.md) covers setup and the project's
fail-closed principles.

```bash
git clone https://github.com/sx4im/resultseal.git
cd resultseal
python -m venv .venv && source .venv/bin/activate
make install   # editable install with dev tools
make all       # tests, ruff, mypy --strict, build
```

<a href="https://github.com/sx4im/resultseal/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sx4im/resultseal" alt="Contributors" />
</a>

## License

[MIT](https://github.com/sx4im/resultseal/blob/master/LICENSE)
