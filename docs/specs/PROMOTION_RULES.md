# Promotion Rules

The rules engine must be a pure function: same envelope, contract, and reference clock produce the same decision.

## Default table

| Input condition | Decision |
|---|---|
| No dispatch record | Block with `no_dispatch` and `unknown`. |
| Transport error | Block with `transport_error`. |
| Parse failure | Block with `parse_error`. |
| Empty payload without explicit sentinel | Block with `empty`, never `not_found`. |
| Explicit approved not-found sentinel | Permit `not_found` if source and target match. |
| Missing required fields | Block with `partial`. |
| Old observation revision or timestamp | Block with `stale`. |
| Source or target mismatch | Block with `source_mismatch`. |
| Claimed write without effect evidence | Block with `unverified_effect`. |
| All required fields and evidence satisfy contract | Return `sealed`. |

## Security properties

Rules cannot execute expressions, call tools, access the filesystem, access the network, inspect environment variables, or invoke a model. Contract values are data only. If a contract asks for unsupported semantics, the result is `unknown` with a configuration error.

## Test obligations

Add table-driven tests for every row. Add metamorphic tests showing that removing required evidence cannot improve a decision, changing the target cannot preserve a seal, and changing the source revision to an older value cannot preserve freshness.

