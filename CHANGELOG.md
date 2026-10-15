# Changelog

## [0.2.0] — 2026-10-15

### Added

- Public Python API at the package root: `resultseal.check()` returns a
  `CheckResult` (decision, truth state, reason codes, envelope, payload);
  `resultseal.seal()` returns the verified payload or raises
  `BlockedObservation`; `resultseal.load_contract()` accepts a path or a
  mapping. `CheckResult.record()` is byte-identical to
  `resultseal check --format json` (D26).
- Framework examples for smolagents (#19) and AutoGen (#13), both run end to
  end against the real frameworks.
- Fixtures for a DynamoDB empty `Query` (#24) and Elasticsearch zero hits
  (#23, PR #25).
- The wheel ships a `py.typed` marker.
- Python 3.14 support.

### Fixed

- **Stale observations could seal.** An unquoted YAML `observed_at` loads as
  a `datetime`; the adapter discarded it and substituted the reference
  clock, so arbitrarily old evidence passed `max_age_seconds` freshness. The
  clock is now used only when `observed_at` is absent (D25).
- `resultseal replay` reported a correctly rejected fixture as a failure
  (exit 3) and stopped, so `resultseal replay fixtures/*.yaml` never reached
  the fixtures after `unsafe-input.yaml`. Rejections that match their
  expected codes now print `MATCH` and the run continues (D27).
- Inputs that crashed with a traceback instead of a stable error code:
  construct-time YAML errors (`AttributeError` from a misnamed exception
  class), tagged scalars that do not parse under their tag (`!!int abc`),
  JSON nesting deep enough to exhaust the decoder's recursion limit, and a
  non-string `kind`.
- Deeply nested flow YAML took ~28 s to reject because PyYAML's scanner is
  quadratic in nesting depth; the depth bound is now enforced while
  scanning, before parsing, and fails in milliseconds.
- YAML timestamps inside payloads crashed content hashing; they now
  canonicalize as ISO-8601 (PR #26).
- Malformed contract field types now consistently raise `CONTRACT_INVALID`
  (PR #26).
- The GitHub Pages playground disagreed with the engine: its "Complete MCP
  result" preset would be blocked by ResultSeal, and one preset contract was
  invalid. The playground now runs a port of the engine that CI checks
  against the package on every fixture and preset.

### Changed

- Framework examples delegate to `resultseal.seal` and load their contract
  once, instead of re-implementing the pipeline per call.
- The package version is single-sourced in `src/resultseal/_version.py`.
- Development status is now Beta.
- README rewritten around the public API; its Python examples are executed
  by the test suite. The fixture catalog now lists every shipped fixture.

## [0.1.3] — 2026-09-12

### Added

- HTTP 404 structured-error fixture (`fixtures/http-404-structured-error.yaml`)
  proving that error response bodies cannot be promoted to domain `not_found`
  claims; transport failures block with `unknown` / `TRANSPORT_FAILED` (#18, PR #22).
- GraphQL HTTP 200 partial-error fixture (`fixtures/graphql-error-200.yaml`)
  demonstrating fail-closed `partial` evaluation (`MISSING_REQUIRED_FIELD`) for
  non-empty response envelopes carrying `data: null` and errors (#8, PR #16).
- Redis GET key-miss nil response fixture (`fixtures/redis-nil-response.yaml`)
  demonstrating `empty` classification on cache misses (#12, PR #14).
- Agent framework tool guard examples: LangGraph (`examples/langgraph_tool_guard.py`),
  CrewAI (`examples/crewai_tool_guard.py`), LlamaIndex (`examples/llamaindex_tool_guard.py`),
  and LangChain (`examples/langchain_tool_guard.py`).
- High-resolution transparent vector brand assets and GitHub Pages playground.

## [0.1.2] — 2026-09-03

### Added

- Interactive CLI verdict coloring (`feat(cli): color interactive verdicts`):
  highlights `sealed` / `MATCH` in green and `blocked` / `MISMATCH` in red on
  interactive terminals (`sys.stdout.isatty()`). Respects `NO_COLOR` and leaves
  JSON output byte-deterministic (#4, PR #6).
- Offline Pydantic-AI agent tool result guard example (`examples/pydantic_ai_guard.py`)
  demonstrating observation integrity validation before returning tool results to
  the agent loop (#3, PR #5).
- SQL empty-result fixture (`fixtures/sql-empty-query.yaml`) demonstrating that database
  query empty results fail-closed as `EMPTY_WITHOUT_NOT_FOUND_SENTINEL` (#2).
- Hardened core invariants (D23): fail-closed NOT_FOUND claim checks, DISPATCHED
  transport state checking, MappingProxyType immutable metadata, future timestamp
  rejection, and float -0.0 canonical JSON normalization.
- Three fixtures from production LinkedIn automation integration (D22):
  `bare-json-payload.yaml`, `empty-body-effect.yaml`, and
  `effect-with-recorded-facts.yaml`.

## 0.1.1 — 2026-08-23

### Fixed

- Shipped examples now work end to end: `examples/http_empty.json` carries
  its body under the field name the HTTP adapter actually hashes (`body`,
  previously the unread `response_body`, so the envelope hashed null);
  `examples/mcp_result.json` gained the `source_ref`/`target_ref` identity
  fields every adapter input requires; and new
  `examples/customer_contract.json` makes both runnable through
  `resultseal check`. Example validation no longer skips raw-response
  shapes — each must normalize into an envelope satisfying
  `schemas/observation-envelope.v1.json` (D21).

### Added

- Tag-driven publish workflow: a `v*` tag runs the full gate suite,
  builds and smoke-installs the wheel, then uploads to PyPI via trusted
  publishing and attaches artifacts to a GitHub Release.
- A naive-but-parseable `observed_at` under `max_age_seconds` freshness
  now blocks as `unknown`/`SCHEMA_INVALID` instead of escaping `evaluate`
  as an unclassified `TypeError` (D18).
- `resultseal replay --format json --redact` now redacts before
  fingerprinting, matching `resultseal check`, so the printed
  `deterministic_fingerprint` verifies against the printed record.
  Redacted replay output differs byte-wise from 0.1.0; unredacted output
  is unchanged (D19).

### Changed

- Internal readability cleanups with no behavior change: shared
  expectation-matching and record-pipeline helpers, single homes for
  `format_clock` and the fingerprint key, unused parameters removed (D20).

## 0.1.0 — 2026-08-22 (public alpha)

First implementation release. Offline, deterministic observation-integrity
gate for AI-agent tool results.

### Added

- Typed, frozen observation envelope and contract models with strict
  construction (`models.py`); stable error taxonomy mapping failures to
  public reason codes and CLI exit codes (`errors.py`).
- Canonical JSON serialization, `content_hash`, and self-excluding decision
  fingerprints (`canonical.py`).
- Pure promotion rules engine with documented precedence, natural-order
  source-version comparison, and injected clock (`rules.py`).
- Bounded safe input loading: size/depth/node/string limits before parse;
  YAML restricted to an explicit tag allowlist with anchors/aliases rejected;
  path containment helpers (`limits.py`, `safeio.py`).
- Contract and self-contained fixture loaders (`contracts.py`,
  `fixtures.py`); shipped fixtures embed their contracts inline.
- HTTP/JSON, MCP-style, and stdio normalizers establishing structural facts
  only (`normalize.py`).
- CLI: `resultseal version | validate | check | replay` with stable exit
  codes (0/1/2/3) and deterministic JSON or Markdown reports (`cli.py`,
  `report.py`).
- Reason-code `PROTOCOL_CONFLICT` for self-contradicting protocol results
  (e.g. MCP `isError: true` alongside success-shaped content), added per the
  ERROR_CODES extension process.
- Contract schema v1 gains optional `min_source_version` (additive D8).

### Guarantee scope

Deterministic given identical inputs and a pinned reference clock. Reports
and fingerprints never contain wall-clock values. Max-age freshness uses the
injected clock only. See docs/specs/THREAT_MODEL.md for the security boundary: this
tool protects the local promotion decision, not external systems.
