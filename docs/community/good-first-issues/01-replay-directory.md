---
title: "CLI: let `resultseal replay` accept a directory of fixtures"
labels: enhancement, good first issue
---

### Problem

`resultseal replay` only accepts file paths, so the README command
`resultseal replay fixtures/*.yaml` depends on the shell expanding the glob.
Windows `cmd` and PowerShell do not expand it, and passing the directory fails:

```console
$ resultseal replay fixtures/
resultseal: PARSE_FAILED: fixture file could not be read ([Errno 21] Is a directory: 'fixtures')
$ echo $?
2
```

### Desired implementation

1. In `src/resultseal/cli.py` (`_run_replay`), expand every argument that is
   a directory into the `*.yaml` and `*.yml` files directly inside it
   (not recursive), sorted by name so output order is deterministic.
2. A directory with no fixture files is an invalid invocation: raise
   `InvalidArgumentError` (exit code 2) with a message naming the directory.
3. File arguments keep working exactly as today, and files and directories
   can be mixed.
4. Document the new form in `docs/specs/CLI_CONTRACT.md` and add
   `resultseal replay fixtures/` to the README's CLI section.

### Tests to add (`tests/test_cli.py`)

- Replaying `fixtures/` matches every shipped fixture and exits 0, with the
  same lines as `replay fixtures/*.yaml`.
- An empty directory exits 2.

### Verification

```bash
resultseal replay fixtures/
pytest tests/test_cli.py
ruff check .
mypy src
```
