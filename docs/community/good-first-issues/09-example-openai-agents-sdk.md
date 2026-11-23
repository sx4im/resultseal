---
title: "Add OpenAI Agents SDK tool guard example"
labels: documentation, enhancement, help wanted, good first issue
---

### Problem

ResultSeal has guard examples for seven frameworks but none for the
[OpenAI Agents SDK](https://github.com/openai/openai-agents-python), one of
the most used agent frameworks. Its `@function_tool` results go straight
back to the model, so an empty lookup becomes "that customer does not
exist". When a function tool raises, the SDK's default
`failure_error_function` tells the model only "An error occurred while
running the tool.", so the example has to pass its own
`failure_error_function` that forwards ResultSeal's block reason.

### Desired implementation

Create `examples/openai_agents_tool_guard.py`, following
`examples/smolagents_tool_guard.py`:

1. Load `examples/customer_contract.json` and guard the result with
   `resultseal.seal`, using `source_ref: "mcp://crm-server"` and
   `target_ref: "customer:42"`.
2. Keep `from agents import function_tool` inside a `build_tool()` factory
   so the module imports without the SDK installed.
3. Decorate the tool with
   `@function_tool(failure_error_function=...)`, using a function that
   returns `str(error)` for a `BlockedObservation` and the SDK's generic
   message for any other exception, so internal errors stay hidden.
4. The module docstring says how to install the SDK
   (`pip install openai-agents`) and what the model sees when the guard
   raises.
5. Add a row to the "Framework integrations" table in the README.

### Tests to add (`tests/test_examples.py`)

Use `runpy.run_path`, like the existing example tests:

- An empty result `[]` raises `BlockedObservation` with
  `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`.
- `{"customer_id": "42", "name": "Ada"}` seals and is returned unchanged.
- The error function returns the block reason for a `BlockedObservation`
  and the generic message for a `RuntimeError`.

Run the example against the real SDK before opening the PR, and say in the
PR how you ran it. A `FunctionTool` can be invoked without a model; see the
SDK's tools documentation.

### Verification

```bash
pytest tests/test_examples.py
ruff check .
mypy src
```
