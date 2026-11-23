---
name: resultseal-contracts
description: Write, validate and explain ResultSeal contracts that guard MCP tool results in this project. Use when the user wants an MCP tool's results checked before they are trusted, asks why a tool result was blocked by ResultSeal, or mentions .resultseal/contracts.
---

# ResultSeal contracts for MCP tools

The ResultSeal plugin runs after every MCP tool call. When
`.resultseal/contracts/<tool_name>.json` (or `.yaml`) exists for the tool, the
hook checks the result against it and blocks results that are empty, errored
or missing required fields. Tools without a contract are not checked.

## Add a contract for a tool

1. Find the exact tool name. MCP tools are named `mcp__<server>__<tool>`, for
   example `mcp__crm__get_customer`. The file name must match it exactly.
2. Decide what a trustworthy result must contain. Pick the top-level fields
   the answer depends on; do not list every field the tool returns.
3. Write `.resultseal/contracts/<tool_name>.json`:

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

4. Validate it: `resultseal validate .resultseal/contracts/<tool_name>.json`.
   The command must print `valid (contract)`. Install the CLI with
   `pipx install resultseal` if it is missing.

## Choosing fields

- `claim_type`: use `found` or `read_complete` for lookups and reads. Use
  `not_found` only when the server returns an explicit absence value, and set
  `not_found_sentinel` to that value (for example `"NOT_FOUND"`); an empty
  list or object never proves absence.
- `required_fields`: top-level keys of the result object. A JSON document
  returned as text content is parsed before the check.
- `freshness`: keep `{"mode": "not_required"}`. MCP results carry no source
  version or observation time, so `source_version` mode always blocks and
  `max_age_seconds` cannot detect staleness in a hook.
- `effect_observed` / `task_complete` with `effect_evidence_required: true`
  always block in the hook, because MCP results carry no evidence references.
- `source_ref` and `target_ref` are labels for the decision record. The hook
  copies them into the observation, so they cannot mismatch.

## When a result is blocked

The hook reports the truth state and reason codes. Do not state the blocked
result as fact. Explain the code to the user and retry or ask for direction:

| Reason code | Meaning |
|---|---|
| `EMPTY_WITHOUT_NOT_FOUND_SENTINEL` | Empty result; it does not prove the record is absent. |
| `PROTOCOL_CONFLICT` | The tool set `isError: true`; its content is an error, not an answer. |
| `MISSING_REQUIRED_FIELD` | A field the contract requires is missing. |
| `UNVERIFIED_EFFECT` | An effect claim without evidence references. |

The reason code list and promotion rules are in
https://github.com/sx4im/resultseal/blob/master/docs/specs/PROMOTION_RULES.md.
