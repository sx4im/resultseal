# Report Format

Every evaluation produces a normalized decision record.

```json
{
  "resultseal_version": "0.1.0",
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

Markdown reports must be readable by a developer in a terminal. JSON reports must be machine-consumable and stable across replay. Never include raw secrets or unrestricted payloads in reports.

