# Fixture Catalog

Every fixture under `fixtures/` is self-contained (input, inline contract,
expectation) and replays with `resultseal replay fixtures/<name>.yaml`.
`tests/test_fixture_matrix.py` replays all of them on every CI run.

## Core semantics

| Fixture | Expected state | Expected result |
|---|---|---|
| `empty-result.yaml` | `empty` | Block not-found promotion. |
| `explicit-not-found.yaml` | `not_found` | Seal not-found if source/target match. |
| `partial-response.yaml` | `partial` | Block. |
| `stale-response.yaml` | `stale` | Block. |
| `wrong-target.yaml` | `source_mismatch` | Block (`TARGET_MISMATCH`). |
| `unverified-write.yaml` | `unverified_effect` | Block effect claim. |
| `no-dispatch-success-claim.yaml` | `unknown` | Block task success. |
| `complete-fresh-result.yaml` | `sealed` | Seal when contract evidence is satisfied. |
| `malformed-json.yaml` | `parse_error` | Block and return stable diagnostic. |
| `unsafe-input.yaml` | unsafe-input error | Reject before evaluation. |

## Integration lessons

| Fixture | Expected state | Expected result |
|---|---|---|
| `bare-json-payload.yaml` | `empty` | Block: a `kind: json` payload must ride under `body`; top-level fields are not the payload. |
| `empty-body-effect.yaml` | `empty` | Block: a body-less success (e.g. HTTP 204) is an empty observation, never an effect. |
| `effect-with-recorded-facts.yaml` | `sealed` | Seal: record the structural fact that did happen (status as body + evidence ref) and the effect claim verifies. |

## Real-world backends

| Fixture | Backend response | Expected state | Expected result |
|---|---|---|---|
| `sql-empty-query.yaml` | SQL query returning no rows (`[]`) | `empty` | Block: zero rows is not proof of absence. |
| `redis-nil-response.yaml` | Redis `GET` key miss (`nil`) | `empty` | Block: a cache miss is not a not-found claim. |
| `elasticsearch-zero-hits.yaml` | Search with `hits.total.value: 0` | `partial` | Block (`MISSING_REQUIRED_FIELD`): a zero-hit envelope carries no document. |
| `dynamodb-empty-query.yaml` | DynamoDB `Query` with `Items: []`, `Count: 0` | `partial` | Block (`MISSING_REQUIRED_FIELD`): HTTP 200 metadata is not a record. |
| `graphql-error-200.yaml` | GraphQL HTTP 200 with `data: null` and `errors` | `partial` | Block (`MISSING_REQUIRED_FIELD`): partial-error envelopes never seal. |
| `http-404-structured-error.yaml` | HTTP 404 with a JSON error body | `unknown` | Block (`TRANSPORT_FAILED`): an error body is transport evidence, not domain `not_found`. |
