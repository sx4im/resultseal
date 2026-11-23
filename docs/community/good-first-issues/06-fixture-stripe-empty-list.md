---
title: "Add Stripe empty list response fixture"
labels: enhancement, help wanted, good first issue
---

### Problem

Stripe's list endpoints return HTTP 200 with an empty `data` array when
nothing matches, for example a customer search by email:

```json
{
  "object": "list",
  "data": [],
  "has_more": false,
  "url": "/v1/customers"
}
```

An agent that reads this as "no such customer" is treating a list envelope
as proof of absence. ResultSeal already blocks it; a fixture pins that
behavior for a backend many agents call.

### Desired implementation

Create `fixtures/stripe-empty-list.yaml`, following
`fixtures/dynamodb-empty-query.yaml`:

1. `name: stripe-empty-list`, `claim_type: found`
2. Contract requiring `id` and `email`, with
   `source_ref: stripe://v1/customers` and `target_ref: customer:ada@example.com`
3. Input:
   - `kind: http_json`, `status_code: 200`
   - matching `source_ref` / `target_ref`
   - `tool_name: stripe_list_customers`
   - `body`: the list envelope above
4. Expected outcome:
   - `decision: blocked`
   - `truth_state: partial`
   - `reason_codes: [MISSING_REQUIRED_FIELD]`
5. Add a row to the "Real-world backends" table in
   `docs/specs/FIXTURE_CATALOG.md`.

### Verification

```bash
resultseal replay fixtures/stripe-empty-list.yaml   # MATCH: stripe-empty-list -> partial/blocked
pytest tests/test_fixture_matrix.py tests/test_cli.py
ruff check .
mypy src
```
