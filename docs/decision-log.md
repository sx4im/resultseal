# Decision Log

Concise, append-only record of decisions made during the build. Newest entries at the bottom.

## D1 — 2026-08-21 — Implementation target and repository layout

The documentation archive `resultseal_claude_code_handoff/` is treated as a read-only source of truth. The ResultSeal implementation lives at this repository's root with the layout required by the handoff: `src/resultseal/`, `tests/`, `docs/`, `fixtures/`, `examples/`, `schemas/`, `pyproject.toml`, `Makefile`. The archive itself is never modified.

## D2 — 2026-08-21 — No chat-handoff files

`MASTER_BUILD_PROMPT.md` and phase prompts ask for a `STATESEAL_CHAT_HANDOFF.md` after each phase. The build directive for this session explicitly forbids creating chat handoff files or session-transfer instructions. The directive wins. Continuity is carried by `IMPLEMENTATION_STATUS.md`, `docs/test-evidence.md`, and this log instead. Deviation recorded here once; not repeated per phase.

## D3 — 2026-08-21 — pytest pin relaxed to `>=8,<10`

The handoff `pyproject.toml` pins `pytest>=8,<9`. The offline environment provides only pytest 9.0.3, so the pin as written can never pass locally. Relaxed to `pytest>=8,<10`; tests avoid pytest-9-only APIs so they also run under 8.x in CI.

## D4 — 2026-08-21 — Build via `uv build`; `python -m build` unavailable

The `build` package cannot be installed (no network). The environment provides `uv` with cached `hatchling` wheels; `uv build --offline` was verified to produce both sdist and wheel using the handoff's hatchling backend. The Makefile `build` target uses `python -m build` when available and falls back to `uv build`. CI keeps `python -m build`.

## D5 — 2026-08-21 — Fixture bundle format defined

The docs name ten `.yaml` fixtures but never define the bundle schema. Filled the gap minimally: a fixture is a single YAML document with three top-level keys — `fixture` (name, expected truth state, expected decision, expected reason codes), `contract` (inline contract object), and `observation` (kind + raw response fields for one of the three adapters). Strict structure, bounded sizes, safe-load only. Documented in `docs/fixture-format.md` when implemented in Phase 4.

## D6 — 2026-08-21 — Fingerprint definition

`deterministic_fingerprint` = `"sha256:" + hex(sha256(canonical_json(decision_record minus deterministic_fingerprint field)))`. Canonical JSON = UTF-8, sorted keys recursively, separators `,`/`:`, no NaN/Inf, integers preserved. Recorded here because REPORT_FORMAT shows the field but not its derivation.

## D7 — 2026-08-21 — PyYAML is the single declared runtime dependency

Conflict: the pyproject template sets `dependencies = []`, but all shipped fixtures are `.yaml` and CONFIG_CONTRACT permits "a restricted YAML representation" "only when a safe parser is available". Hand-writing a YAML parser was rejected (risk, scope). Decision: declare `pyyaml>=6,<7` as the sole runtime dependency — justified by THREAT_MODEL's "Safe parser only" control (`yaml.safe_load`, custom tags rejected by constructing a loader whose constructors are cleared), MIT license, no transitive dependencies, offline-installable from cache. JSON paths work without PyYAML. Every other dependency remains standard library.

## D8 — 2026-08-22 — Contract schema gains optional `min_source_version`

`contract.v1.json` permitted `freshness.mode = source_version` with no field
carrying the baseline version, yet shipped fixtures must distinguish
`revision-17` (seal) from `revision-1` (stale). Added optional string field
`min_source_version` (≤256 chars); comparison is natural ordering (digit runs
numeric, text runs lexicographic, prefix-first). A `source_version` contract
without it is `CONTRACT_INVALID`. Additive; validated against the shipped
schema in `tests/test_schemas.py`. Full rationale is embedded in this entry and in D9-D11 below.

## D9 — 2026-08-22 — Fixtures embed their contract inline

Shipped fixture YAMLs gain a top-level `contract:` block so each is
self-contained and `resultseal replay <fixture>` works standalone. No
sibling-file lookup or built-in default contracts; a contract-less fixture
loads for validation but cannot be replayed (exit 2). The ten received
fixture files are edited once for this reason; no other archive doc changes.

## D10 — 2026-08-22 — Clock injection and determinism boundary

Rules take an injected `ReferenceClock`; CLI exposes `--now ISO-8601` on
`check`/`replay` (default: current UTC, used only for max-age evaluation).
Reports and fingerprints never contain wall-clock values, so replays of the
shipped fixtures (all source_version freshness) are byte-identical; max-age
users needing replay-stable verdicts must pin `--now`.

## D11 — 2026-08-22 — Envelope identity defaults

`observation_id`/`tool_call_id` default to `obs-<12hex>`/`call-<12hex>`
derived from the payload content hash when the caller does not supply them;
`observed_at` defaults to the injected clock. None of these enter the
decision record, keeping replay deterministic.

## D12 — 2026-08-22 — Sealed truth-state convention

A sealed `not_found` claim reports truth_state `not_found` (an explicit,
provable absence); every other sealed path reports truth_state `sealed`.
This is the unique reading under which both shipped positive fixtures
(`explicit-not-found`: not_found/sealed; `complete-fresh-result`:
sealed/sealed) are simultaneously valid.

## D13 — 2026-08-22 — No target_mismatch truth state

The v1 envelope schema defines exactly one identity truth state,
`source_mismatch`; `TARGET_MISMATCH` exists only as a reason code. Rules
classify identity mismatches as `source_mismatch` and name the failing
leg(s) in reason_codes. The wrong-target fixture's expected truth_state is
normalized from `target_mismatch` to `source_mismatch` in the D9 fixture
pass, per FIXTURE_CATALOG's explicit "`source_mismatch` or
`target_mismatch`" allowance. Schema and PROTOCOL_SPEC win over fixture
prose.

## D14 — 2026-08-22 — Shipped example corrected for D8

`examples/minimal_contract.json` declared `freshness.mode=source_version`
with no baseline, which D8 defines as `CONTRACT_INVALID`. Shipping an
invalid example contradicts the acceptance requirement that "JSON schemas validate all shipped examples"; its mode was changed to `not_required` (the example
is sentinel-focused). Recorded as a one-time archive-example correction.

## D15 — 2026-08-22 — Readiness classification: READY FOR PUBLIC ALPHA

The deterministic core, three normalizers, CLI, reports, fixture matrix,
security scans, and packaging all pass their gates offline; the acceptance
checklist is fully ticked with evidence. Zero external integrations exist,
so beta is not claimable. Limitations documented in the CHANGELOG guarantee-scope paragraph.

## D16 — 2026-08-22 — Chat handoff file reinstated

Prior-session D2 forbade chat-handoff files under a directive that is no
longer active. The current CLAUDE.md mandates `STATESEAL_CHAT_HANDOFF.md`
after every session. This file now exists and supersedes D2. The stale
"standing constraints" lines in IMPLEMENTATION_STATUS.md (read-only archive
directory that has since been committed into the repo; no-handoff rule) are
corrected in the same commit.

## D17 — 2026-08-22 — Public/private documentation split

The public repository now carries only open-source-facing documentation:
the normative specs (PRODUCT_SPEC, ARCHITECTURE, PROTOCOL_SPEC,
PROMOTION_RULES, ERROR_CODES, CLI_CONTRACT, REPORT_FORMAT,
CONFIG_CONTRACT, ADAPTERS, FIXTURE_CATALOG, NON_GOALS, THREAT_MODEL),
standard community files, code, tests, schemas, fixtures, and this log.

Internal working documents — AI-assistant instructions, phase prompts,
session status/handoff/evidence logs, the requirements matrix, release and
discovery plans, research-pipeline outputs, and the acceptance checklist —
are maintained locally only and are listed in `.gitignore`. References to
those files in earlier entries below refer to local maintainer files; the
decisions themselves remain fully described here.
