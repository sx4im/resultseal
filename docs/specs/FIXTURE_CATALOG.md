# Fixture Catalog

| Fixture | Expected state | Expected result |
|---|---|---|
| `empty-result.yaml` | `empty` | Block not-found promotion. |
| `explicit-not-found.yaml` | `not_found` | Seal not-found if source/target match. |
| `partial-response.yaml` | `partial` | Block. |
| `stale-response.yaml` | `stale` | Block. |
| `wrong-target.yaml` | `source_mismatch` or `target_mismatch` | Block. |
| `unverified-write.yaml` | `unverified_effect` | Block effect claim. |
| `no-dispatch-success-claim.yaml` | `unknown` | Block task success. |
| `complete-fresh-result.yaml` | `complete` | Seal when contract evidence is satisfied. |
| `malformed-json.yaml` | `parse_error` | Block and return stable diagnostic. |
| `unsafe-input.yaml` | unsafe-input error | Reject before evaluation. |
| `bare-json-payload.yaml` | `empty` | Block: a `kind: json` payload must ride under `body`; top-level fields are not the payload. |
| `empty-body-effect.yaml` | `empty` | Block: a body-less success (e.g. HTTP 204) is an empty observation, never an effect. |
| `effect-with-recorded-facts.yaml` | `sealed` | Seal: record the structural fact that did happen (status as body + evidence ref) and the effect claim verifies. |

