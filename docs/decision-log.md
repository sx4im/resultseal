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

## D18 — 2026-08-22 — Naive `observed_at` is schema-invalid under max-age freshness

`_parse_timestamp` accepted offset-naive ISO-8601 values; the subsequent
age subtraction against the timezone-aware reference clock then escaped
`evaluate` as a raw `TypeError` instead of a classified outcome. An
observation whose `observed_at` carries no UTC offset cannot be compared
to the reference clock, so it is refused exactly like an unparseable
timestamp: blocked/unknown with reason code `SCHEMA_INVALID`. Fail-closed;
symmetric with `ReferenceClock`'s aware-only invariant. The operator-supplied
`--now` flag keeps assuming UTC for naive input (trusted invocation flag,
per D10). Found in the 2026-08-22 readability audit.

## D19 — 2026-08-22 — Redaction always precedes fingerprinting

`resultseal replay --format json --redact` stamped the fingerprint over the
pre-redaction record, printing a `deterministic_fingerprint` that did not
verify against the record beside it, and disagreed with `resultseal check`
for identical content. The record pipeline is now redact-then-fingerprint
everywhere; a redacted report's fingerprint is computed over exactly the
redacted record shown. Replay outputs with redaction change bytes relative
to 0.1.0; unredacted output is unchanged. Found in the 2026-08-22
readability audit.

## D20 — 2026-08-22 — Readability audit cleanups (no behavior change)

A senior-review pass over src/ and tests/ landed the following internal
cleanups alongside D18 and D19: the unused `kind` parameter was removed
from all normalizer handlers; `format_clock` and the fingerprint key each
have a single home (`rules.py`, `canonical.py`); `_check_str` is one
validator parameterized by error class; fixture loading threads caller
`Limits` into embedded contracts; `prepare_payload` lost its
never-supplied `limits` argument (nested payloads are documented as
package-default bounds); `expectation_matches` in `fixtures.py` is the
single definition of fixture-expectation semantics, used by both the CLI
and the fixture-matrix tests; build → redact → fingerprint is one shared
record helper; safeio's root-kind guard is a single branch; fixture
`reason_codes` no longer coerce falsy non-lists; the purity scan lost an
identity helper; and minor typing/comment fixes landed in `contracts.py`,
`errors.py`, and two test files. All three gates (ruff, mypy strict,
pytest) run clean after each individual change.

## D21 — 2026-08-23 — Shipped examples corrected and made runnable

The acceptance requirement "JSON schemas validate all shipped examples"
was met only nominally: `tests/test_schemas.py` skipped exactly the two
raw-response examples, and neither worked through its adapter.
`examples/http_empty.json` carried its body under `response_body`, a field
name no adapter reads, so the envelope's content hash covered null instead
of the empty body the example is about; the field is renamed to `body`.
`examples/mcp_result.json` lacked `source_ref`/`target_ref`, so it could
not normalize at all; identity fields consistent with its payload are
added. New `examples/customer_contract.json` pairs with both, making
`resultseal check examples/... --contract examples/...` runnable end to
end (sealed for the MCP result, blocked/empty for the HTTP 200). Example
validation is strengthened from skip to assertion: every response example
must normalize into an envelope satisfying
`schemas/observation-envelope.v1.json`. This extends D14's precedent:
shipping an example that contradicts the implementation's own validation
undermines the acceptance evidence, so examples are corrected once,
recorded here. README install instructions changed to source install until
the package is published to PyPI.

## D22 — 2026-08-23 — Integration lessons: json body wrapper and body-less effect claims

The first production integration (a cron agent gating LinkedIn API
results) surfaced two adapter-level lessons. Neither changes engine
behavior; both are now pinned as executable documentation.

1. The most common integration mistake is passing the payload object as
   the whole `kind: json` input. The adapter reads only `body`, so the
   observation is empty and blocks as `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`
   — fail-closed, but the code does not name the mistake. Pinned by
   `fixtures/bare-json-payload.yaml`; a JSON-adapter section in
   ADAPTERS.md now states the rule: top-level input fields are
   observation metadata, never the payload.
2. Body-less success protocols (HTTP 204 DELETE) produce empty
   observations, which can never support an effect claim — correctly
   blocked (`fixtures/empty-body-effect.yaml`). The integration pattern
   is to record the structural fact that did occur (the HTTP status) as
   the payload with an `evidence_refs` reference, letting an
   `effect_observed` contract seal on real evidence
   (`fixtures/effect-with-recorded-facts.yaml`). ADAPTERS.md documents
   this as "never fabricate semantics; record facts."

Both fixtures replay green through the existing fixture matrix; no
source change was required, which is itself the finding: the engine
already drew the right line in both cases.

## D23 — 2026-09-01 — Hardening core decision invariants, model immutability, and canonical serialization

A deep code audit identified and resolved five safety edge cases:

1. `ClaimType.NOT_FOUND` previously bypassed sentinel validation when evaluated against populated payloads, leading to false-positive `SEALED` decisions for existing entities. `evaluate()` now strictly blocks non-sentinel matches as `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`.
2. `TransportState.DISPATCHED` was omitted from transport checks, allowing in-flight/unexecuted dispatches with attached payloads to bypass transport checks. It is now blocked as `NO_DISPATCH`.
3. `ObservationEnvelope.metadata` passed direct mutable dicts to the dataclass; `__post_init__` now converts any `Mapping` to an immutable `MappingProxyType`.
4. `FreshnessMode.MAX_AGE_SECONDS` evaluated `age = clock.now - observed` and passed negative age (`observed` in the future) as `<= max_age_seconds`. Future timestamps are now rejected as `STALE_OBSERVATION`.
5. Canonical JSON now normalizes float `-0.0` to `0.0` to eliminate content-hash divergence for mathematically equivalent floating-point zeros.

