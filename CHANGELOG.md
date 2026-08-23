# Changelog

## Unreleased

### Added

- Three fixtures distilled from the first production integration (a
  gated LinkedIn auto-poster): `bare-json-payload.yaml` pins the most
  common integration mistake — a `kind: json` payload passed as the
  whole input instead of riding under `body` — blocking as
  `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`; `empty-body-effect.yaml` and
  `effect-with-recorded-facts.yaml` document the body-less-success
  pattern as a blocked/sealed contrast pair (HTTP 204 effect claims).
  ADAPTERS.md gains a JSON-adapter section and a body-less-success
  section; FIXTURE_CATALOG rows added (D22).

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
