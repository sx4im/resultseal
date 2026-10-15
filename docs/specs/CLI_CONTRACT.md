# CLI Contract

The executable is `resultseal`.

| Command | Purpose | Exit behavior |
|---|---|---|
| `resultseal version` | Print package version | 0 |
| `resultseal validate PATH` | Validate contracts or fixtures | 0 valid, 2 invalid input, 3 unsafe input |
| `resultseal check RESPONSE --contract CONTRACT` | Normalize and evaluate one response | 0 sealed, 1 blocked/unknown, 2 invalid invocation, 3 unsafe input |
| `resultseal replay FIXTURE [FIXTURE ...]` | Run deterministic fixtures and print one result each | 0 if every expected outcome matches, 1 any mismatch, 2 invalid fixture, 3 unsafe fixture document |

A fixture whose expectation is `decision: rejected` matches when preparing
its input raises an error whose code (or a code it specializes) covers the
expected `reason_codes`; it is reported as `MATCH: <name> -> rejected (<CODE>)`
and the run continues.

## Output

JSON output must have stable key ordering and no nondeterministic fields unless explicitly requested. Markdown output must show input, normalized state, claim, decision, reason codes, and evidence references. Errors must be actionable and must never be silently swallowed.

## CLI safety

The CLI must not accept arbitrary Python expressions, shell fragments, URLs, remote references, or dynamic imports through configuration. All input is treated as untrusted data.

