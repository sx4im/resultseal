# Adapter and Normalization Contracts

Adapters translate external result shapes into the common envelope. They do not decide truth merely from a protocol-level success.

## HTTP/JSON adapter

Input fields may include status code, headers, body, request target, response target, parsed JSON, and observed timestamp. HTTP 2xx may establish `transported` but never automatically establish `complete`, `not_found`, or `sealed`.

## MCP-style adapter

Recognize `structuredContent`, text content, `outputSchema`, and `isError`. Validate structure where a schema exists. Preserve the distinction between a structural result and a semantic result. An empty structured object is not automatically not-found. An `isError` conflict must produce a reason code and safe blocking state.

## Stdio/CLI adapter

Capture exit code, stdout, stderr, command identity, and optional machine-readable output. A zero exit code establishes transport/process completion only. Missing stdout or an absent required field must remain `empty`, `partial`, or `unknown` according to the contract.

## JSON adapter

A `kind: json` input must carry its payload under `body`, exactly like the
HTTP adapter. Top-level input fields other than `body` are observation
metadata, never the payload — an input with identity fields but no `body`
is an *empty* observation and blocks as `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`
(see `fixtures/bare-json-payload.yaml`). This is the most common
integration mistake: passing the payload object itself as the whole input.

## Adapter invariants

Adapters must be deterministic, bounded, redaction-aware, and side-effect-free. They must not execute returned strings, follow URLs, load imports, invoke shells, or send data outside the process.

## Body-less success protocols (effect claims)

Some protocols report success with an empty body — an HTTP 204 DELETE is
the canonical case. An empty observation can never support a claim, so an
adapter that passes the emptiness through will always block as `EMPTY_WITHOUT_NOT_FOUND_SENTINEL` (`fixtures/empty-body-effect.yaml`). The
correct pattern is to record the structural fact the exchange *did*
produce — the HTTP status — as the payload, and reference it in
`evidence_refs`; an `effect_observed` contract then seals on real
evidence (`fixtures/effect-with-recorded-facts.yaml`). Never fabricate
semantics; record facts.

