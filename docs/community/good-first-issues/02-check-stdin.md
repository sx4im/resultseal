---
title: "CLI: read the response from stdin with `resultseal check -`"
labels: enhancement, good first issue
---

### Problem

`resultseal check` needs the tool response in a file. Piping a captured
response straight into it, the usual CLI convention, fails:

```console
$ cat examples/mcp_result.json | resultseal check - --contract examples/customer_contract.json
resultseal: PARSE_FAILED: file could not be read ([Errno 2] No such file or directory: '-')
```

Reading stdin would let people pipe `curl`, `jq` or an MCP client into
ResultSeal in shell scripts and CI without temporary files.

### Desired implementation

1. In `src/resultseal/cli.py`, when the `response` argument is exactly `-`,
   read `sys.stdin.buffer` and parse it with `load_json` (the same bounded
   loader used for files, so the 128 KiB limit still applies and oversized
   input exits 3).
2. Only the response may come from stdin. `--contract -` should exit 2 with
   a clear message.
3. Document `-` in `docs/specs/CLI_CONTRACT.md` and add one piped example to
   the README's CLI section.

### Tests to add (`tests/test_cli.py`)

- A sealed response piped on stdin exits 0 and prints the same record as
  the file form (use `monkeypatch.setattr(sys, "stdin", ...)` with an
  `io.TextIOWrapper(io.BytesIO(...))`).
- Invalid JSON on stdin exits 2.
- `--contract -` exits 2.

### Verification

```bash
cat examples/mcp_result.json | resultseal check - --contract examples/customer_contract.json
pytest tests/test_cli.py
ruff check .
mypy src
```
