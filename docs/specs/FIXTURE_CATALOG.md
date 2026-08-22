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

