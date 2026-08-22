# Adapter and Normalization Contracts

Adapters translate external result shapes into the common envelope. They do not decide truth merely from a protocol-level success.

## HTTP/JSON adapter

Input fields may include status code, headers, body, request target, response target, parsed JSON, and observed timestamp. HTTP 2xx may establish `transported` but never automatically establish `complete`, `not_found`, or `sealed`.

## MCP-style adapter

Recognize `structuredContent`, text content, `outputSchema`, and `isError`. Validate structure where a schema exists. Preserve the distinction between a structural result and a semantic result. An empty structured object is not automatically not-found. An `isError` conflict must produce a reason code and safe blocking state.

## Stdio/CLI adapter

Capture exit code, stdout, stderr, command identity, and optional machine-readable output. A zero exit code establishes transport/process completion only. Missing stdout or an absent required field must remain `empty`, `partial`, or `unknown` according to the contract.

## Adapter invariants

Adapters must be deterministic, bounded, redaction-aware, and side-effect-free. They must not execute returned strings, follow URLs, load imports, invoke shells, or send data outside the process.

