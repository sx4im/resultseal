# Error and Reason Codes

Use stable uppercase reason codes. Initial codes include `NO_DISPATCH`, `TRANSPORT_FAILED`, `PARSE_FAILED`, `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`, `MISSING_REQUIRED_FIELD`, `STALE_OBSERVATION`, `SOURCE_MISMATCH`, `TARGET_MISMATCH`, `UNVERIFIED_EFFECT`, `SCHEMA_INVALID`, `UNSAFE_INPUT`, `LIMIT_EXCEEDED`, `UNSUPPORTED_CLAIM`, `CONTRACT_INVALID`, and `SEALED_WITH_REQUIRED_EVIDENCE`.

Reason codes are part of the public developer experience. Add a code only with documentation, tests, and a changelog entry. Do not use exception messages as the stable API.


## Added codes

`PROTOCOL_CONFLICT` — the adapter's protocol layer contradicts itself (for
example an MCP result carrying `isError: true` alongside success-shaped
content). Added 2026-08-22; documented here, tested in
`tests/test_rules.py::test_protocol_conflict_blocks`, changelog entry in
`CHANGELOG.md`.
