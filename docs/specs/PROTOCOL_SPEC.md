# Observation Integrity Protocol v1

## State vocabulary

| State | Meaning |
|---|---|
| `attempted` | A caller requested an operation. |
| `dispatched` | The request was sent to a tool. |
| `transported` | A response arrived without transport failure. |
| `observed` | A parseable observation was extracted from an identified source. |
| `complete` | Required fields for the contract are present. |
| `empty` | No usable observation was returned and no explicit not-found proof exists. |
| `not_found` | The source returned an explicit contract-approved absence sentinel. |
| `partial` | Some fields arrived but required fields are missing. |
| `stale` | The observation is older than the contract permits. |
| `source_mismatch` | Source, target, or query identity does not match the request. |
| `unverified_effect` | A write response claims success but lacks required effect evidence. |
| `transport_error` | The transport layer reported failure. |
| `parse_error` | The response could not be parsed under the contract. |
| `unknown` | The available evidence is insufficient to classify the result safely. |
| `sealed` | All contract requirements for the declared claim are satisfied. |

## Promotion principle

Promotion is monotonic toward caution. A result may move from raw to normalized, but no rule may turn missing evidence into positive evidence. `empty`, `partial`, `stale`, `source_mismatch`, `unverified_effect`, `transport_error`, `parse_error`, and `unknown` are blocking states by default.

## Required envelope fields

`schema_version`, `observation_id`, `tool_call_id`, `tool_name`, `target_ref`, `transport_state`, `truth_state`, `source_ref`, `observed_at`, `content_hash`, `evidence_refs`, and `reason_codes`.

## Claim classes

MVP claim classes are `found`, `not_found`, `read_complete`, `effect_observed`, and `task_complete`. Each claim class defines required fields and permitted source/evidence rules in a contract. Claims not declared in a contract must be rejected as `unknown`.

