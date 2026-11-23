---
title: "CLI: add help text for every argument and list exit codes in `--help`"
labels: documentation, good first issue
---

### Problem

Most CLI arguments have no description, so `--help` doesn't explain them:

```console
$ resultseal check --help
...
options:
  -h, --help           show this help message and exit
  --contract CONTRACT
  --format {json,md}
  --now NOW            ISO-8601 reference clock.
  --redact FIELD
```

The positional `response`, `fixtures` and `path` arguments are also
undocumented, and the exit codes, which matter most in CI, are only in the
README.

### Desired implementation

In `src/resultseal/cli.py` (`_build_parser` and `_add_common_flags`):

1. Add a short `help=` to every argument: `response`, `--contract`,
   `fixtures`, `path`, `--format`, `--redact`. Describe them the way the
   README and `docs/specs/CLI_CONTRACT.md` do.
2. Add an `epilog` to `check`, `replay` and `validate` that lists that
   command's exit codes (the table under "Check from the command line" in
   the README). Use `formatter_class=argparse.RawDescriptionHelpFormatter`
   so the lines are not rewrapped.

### Tests to add (`tests/test_cli.py`)

- Every option of every subcommand has non-empty help (iterate over the
  parser's `_actions`, skipping `-h`).
- `resultseal check --help` mentions exit code `3`.

### Verification

```bash
resultseal check --help
resultseal replay --help
pytest tests/test_cli.py
ruff check .
mypy src
```
