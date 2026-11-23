---
title: "MCP adapter: read text from the standard `content` array"
labels: enhancement, help wanted, good first issue
---

### Problem

A real MCP `CallToolResult` carries its text in a `content` array:

```json
{"content": [{"type": "text", "text": "{\"customer_id\": \"42\"}"}], "isError": false}
```

The MCP adapter only reads `structuredContent` and a flat `text` key, so a
result passed exactly as an MCP client returns it is treated as empty, even
when it has content:

```python
>>> resultseal.check({"kind": "mcp", "source_ref": "s", "target_ref": "t",
...                   "content": [{"type": "text", "text": "Ada"}], "isError": False},
...                  contract).reason_codes
('EMPTY_WITHOUT_NOT_FOUND_SENTINEL',)
```

Every caller has to flatten `content` into `text` by hand first.
`docs/specs/ADAPTERS.md` already says the adapter recognizes "text content".

### Desired implementation

1. In `src/resultseal/normalize.py` (`_normalize_mcp`), when `text` is
   absent and `content` is a list, join the `text` of every block whose
   `type` is `"text"` with `"\n"`. Ignore other block types (image, audio,
   resource). When `text` is present, it wins and `content` is ignored.
2. Use the joined text as the payload and as the hashed content, exactly as
   a flat `text` would be.
3. Mirror the change in the playground's MCP adapter (`docs/playground.js`,
   the line that reads `raw.text`) so `tests/test_playground.py` keeps
   parity.
4. Document the rule in the MCP section of `docs/specs/ADAPTERS.md` and add
   a `docs/decision-log.md` entry, since it changes an adapter contract.

### Tests to add (`tests/test_normalize_mcp.py`)

- A `content` array with one text block normalizes to that text.
- Two text blocks join with a newline. Image blocks are skipped.
- An empty `content` array still blocks as `empty`.
- `isError: true` with `content` still blocks as `PROTOCOL_CONFLICT`.
- A flat `text` key takes precedence over `content`.

### Verification

```bash
pytest tests/test_normalize_mcp.py tests/test_playground.py
ruff check .
mypy src
```
