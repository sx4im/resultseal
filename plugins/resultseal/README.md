# ResultSeal plugin for Claude Code and Codex

An MCP tool returns `[]`, and the agent tells you the customer does not
exist. This plugin checks MCP tool results against per-tool contracts before
the agent can state them as fact. It blocks results that are empty, carry
`isError: true`, or lack fields the contract requires.

It bundles:

- a `PostToolUse` hook on every `mcp__*` tool, which runs ResultSeal on the
  result when the project has a contract for that tool;
- the `resultseal-contracts` skill, which teaches the agent to write and
  validate those contracts and to explain a block.

## Install

The hook needs Python 3.11+ and the `resultseal` package:

```bash
pipx install resultseal        # or: uv tool install resultseal / pip install resultseal
```

Claude Code:

```bash
claude plugin marketplace add sx4im/resultseal
claude plugin install resultseal@resultseal
```

Codex:

```bash
codex plugin marketplace add sx4im/resultseal
codex plugin add resultseal@resultseal
```

Then open `/hooks` in a Codex session and trust the ResultSeal hook. Codex
skips new or changed hooks until you review them.

## Guard a tool

Create `.resultseal/contracts/<tool_name>.json` in the project, named after
the full MCP tool name:

```json
{
  "schema_version": "1",
  "claim_type": "found",
  "required_fields": ["customer_id", "name"],
  "freshness": {"mode": "not_required"},
  "source_ref": "mcp://crm",
  "target_ref": "crm:customer"
}
```

Saved as `.resultseal/contracts/mcp__crm__get_customer.json`, this contract
makes the hook answer an empty `get_customer` result with:

```text
ResultSeal blocked this mcp__crm__get_customer result as empty
(EMPTY_WITHOUT_NOT_FOUND_SENTINEL) under mcp__crm__get_customer.json. ...
```

Codex replaces the tool result with that message. Claude Code shows it next
to the result. Tools without a contract are not checked, and a sealed result
passes through unchanged.

You can also ask the agent: "add a ResultSeal contract for the
`get_customer` tool".

## What the hook checks

| Result | Decision |
|---|---|
| Empty content, `[]`, `{}` or `""` | blocked: `EMPTY_WITHOUT_NOT_FOUND_SENTINEL` |
| `isError: true` | blocked: `PROTOCOL_CONFLICT` |
| JSON or `structuredContent` missing a required field | blocked: `MISSING_REQUIRED_FIELD` |
| The contract's `not_found_sentinel`, under a `not_found` contract | sealed |
| An object with every required field | sealed |

An MCP result carries no source version, observation time or evidence
references, so keep `freshness` at `not_required` and use `found`,
`read_complete` or `not_found` claims. `source_ref` and `target_ref` label
the decision and are copied from the contract, so identity checks do not
apply in hook mode. The hook uses the tool name for either one a contract
omits; `resultseal validate` and `resultseal.seal` still require both. For
identity checks, guard the tool in your own code with `resultseal.seal`.

If the contract is invalid, or the hook cannot import `resultseal`, guarded
tools are blocked with an explanation rather than passed through.
