---
name: New Test Fixture
about: Add a negative or edge-case test fixture to fixtures/
labels: ["enhancement", "good first issue", "testing"]
---

### Tool observation scenario
What tool or protocol output does this test (e.g., GraphQL, SQL, Redis, CLI)?

### Expected behavior
- Decision: `blocked` or `sealed`
- Truth state: `empty`, `source_mismatch`, `stale`, `parse_error`, etc.
- Reason codes: e.g. `[EMPTY_WITHOUT_NOT_FOUND_SENTINEL]`

### Checklist
- [ ] Added self-contained fixture in `fixtures/<name>.yaml`
- [ ] Replays cleanly: `resultseal replay fixtures/<name>.yaml`
- [ ] Passes fixture matrix: `PYTHONPATH=src pytest tests/test_fixture_matrix.py`
