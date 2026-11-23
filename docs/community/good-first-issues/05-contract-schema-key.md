---
title: "Contracts: accept a `$schema` key so editors can autocomplete them"
labels: enhancement, good first issue
---

### Problem

The repository ships a JSON Schema for contracts
(`schemas/contract.v1.json`), but you can't point an editor at it. Adding the
standard `$schema` key makes VS Code, JetBrains and other editors validate
and autocomplete the file, yet ResultSeal rejects it:

```python
>>> resultseal.load_contract({**contract, "$schema": "https://raw.githubusercontent.com/sx4im/resultseal/master/schemas/contract.v1.json"})
ContractInvalidError: CONTRACT_INVALID: unknown contract fields ($schema)
```

### Desired implementation

1. In `src/resultseal/models.py` (the unknown-field check near
   `"unknown contract fields"`), allow a top-level `$schema` whose value is a
   string. It is ignored: it must not change any decision, record or
   fingerprint. A non-string `$schema` stays `CONTRACT_INVALID`, and every
   other unknown key is still rejected.
2. Add `"$schema": {"type": "string"}` to `properties` in
   `schemas/contract.v1.json`.
3. Mirror the rule in the playground's contract check (`docs/playground.js`,
   the `unknown contract fields` line) so `tests/test_playground.py` keeps
   parity.
4. The contract format is a documented invariant, so add a
   `## D<next number> — <date> — Contracts may carry $schema` entry to
   `docs/decision-log.md`.
5. In the README, show `$schema` in one JSON contract, and mention that YAML
   contracts can use a `# yaml-language-server: $schema=<url>` comment
   instead.

### Tests to add (`tests/test_contracts.py`)

- A contract with a string `$schema` loads and evaluates exactly like the
  same contract without it.
- `"$schema": 1` is rejected with `CONTRACT_INVALID`.
- An unrelated unknown key is still rejected.

### Verification

```bash
pytest tests/test_contracts.py tests/test_schemas.py tests/test_playground.py
ruff check .
mypy src
```
