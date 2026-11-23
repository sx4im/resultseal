---
title: "Add Slack Web API `ok: false` on HTTP 200 fixture"
labels: enhancement, help wanted, good first issue
---

### Problem

Slack's Web API reports most failures with HTTP 200 and `"ok": false`:

```json
{"ok": false, "error": "channel_not_found"}
```

The status code says success, so an agent can read the error envelope as
an answer, or treat `channel_not_found` as confirmed absence when the real
cause may be a missing bot invite or scope. ResultSeal blocks it because the
required fields are absent; a fixture pins that.

### Desired implementation

Create `fixtures/slack-ok-false-200.yaml`, following
`fixtures/graphql-error-200.yaml`:

1. `name: slack-ok-false-200`, `claim_type: found`
2. Contract requiring `channel`, with
   `source_ref: slack://conversations.info` and `target_ref: channel:C0123`
3. Input:
   - `kind: http_json`, `status_code: 200`
   - matching `source_ref` / `target_ref`
   - `tool_name: slack_conversations_info`
   - `body: {ok: false, error: channel_not_found}`
4. Expected outcome:
   - `decision: blocked`
   - `truth_state: partial`
   - `reason_codes: [MISSING_REQUIRED_FIELD]`
5. Add a row to the "Real-world backends" table in
   `docs/specs/FIXTURE_CATALOG.md`.

### Verification

```bash
resultseal replay fixtures/slack-ok-false-200.yaml   # MATCH: slack-ok-false-200 -> partial/blocked
pytest tests/test_fixture_matrix.py tests/test_cli.py
ruff check .
mypy src
```
