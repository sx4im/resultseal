# Changelog

## Unreleased

### Fixed

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
