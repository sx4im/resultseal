---
title: "CLI: print a summary line after `resultseal replay`"
labels: enhancement, good first issue
---

### Problem

`resultseal replay fixtures/*.yaml` prints one `MATCH` / `MISMATCH` line per
fixture and then stops. With 19 fixtures you have to scroll and count to
know whether everything matched, and a single mismatch is easy to miss.

### Desired implementation

1. In `src/resultseal/cli.py` (`_run_replay`), count matched and mismatched
   fixtures. After the per-fixture lines in `--format md` (the default),
   print one summary line:

   ```text
   19 fixtures: 19 matched, 0 mismatched
   ```

2. Leave `--format json` unchanged: it prints one JSON record per fixture,
   and scripts parse those lines.
3. Exit codes stay the same.
4. Update the sample replay output in the README and
   `docs/specs/CLI_CONTRACT.md`.

### Tests to add (`tests/test_cli.py`)

- The last line of a replay over all shipped fixtures reads
  `N fixtures: N matched, 0 mismatched`.
- A run with one mismatching fixture (see
  `test_replay_mismatch_exits_one`) reports `1 mismatched`.
- `--format json` output contains no summary line.

### Verification

```bash
resultseal replay fixtures/*.yaml
pytest tests/test_cli.py tests/test_readme.py
ruff check .
mypy src
```
