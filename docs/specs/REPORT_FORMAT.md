# Report Format

Every evaluation produces a normalized decision record.

```json
{
  "resultseal_version": "0.2.0",
  "decision": "blocked",
  "truth_state": "empty",
  "claim_type": "not_found",
  "reason_codes": ["EMPTY_WITHOUT_NOT_FOUND_SENTINEL"],
  "observation_id": "obs_demo_empty",
  "tool_call_id": "call_demo_empty",
  "source_ref": "fixture://empty-result",
  "evidence_refs": [],
  "deterministic_fingerprint": "sha256:..."
}
```

`resultseal replay --format json` prints a record like the one above for
every evaluated fixture. A `rejected` fixture is refused before evaluation,
so it has no decision record; it prints
`{"decision":"rejected","fixture":"<name>","reason_codes":["<CODE>"]}`.

The same record is available in-process as `resultseal.check(...).record()`.

Markdown reports must be readable by a developer in a terminal. JSON reports must be machine-consumable and stable across replay. Never include raw secrets or unrestricted payloads in reports.

