"""Pure promotion rules.

``evaluate`` is a pure function: identical envelope, contract, payload, and
reference clock always produce an identical ``Evaluation``. It performs no
I/O, reads no environment, consults no wall clock (freshness uses the
injected ``ReferenceClock``), and cannot execute contract data.

Precedence — the first matching row decides; later rows are skipped:

1. no dispatch record            -> blocked/unknown   NO_DISPATCH
2. transport error               -> blocked/unknown   TRANSPORT_FAILED
3. parse failure                 -> blocked           PARSE_FAILED
4. protocol self-contradiction   -> blocked/unknown   PROTOCOL_CONFLICT
5. unusable payload, no sentinel -> blocked/empty     EMPTY_WITHOUT_NOT_FOUND_SENTINEL
6. identity mismatch             -> blocked           SOURCE_MISMATCH / TARGET_MISMATCH
7. freshness failure             -> blocked/stale     STALE_OBSERVATION
8. missing required fields       -> blocked/partial   MISSING_REQUIRED_FIELD
9. claimed effect w/o evidence   -> blocked           UNVERIFIED_EFFECT
10. all conditions satisfied      -> sealed            SEALED_WITH_REQUIRED_EVIDENCE

Sentinel rule: a not-found sentinel matches when the parsed payload equals
the sentinel string or is an object with a top-level value equal to it.

D12 convention: a sealed ``not_found`` claim keeps truth_state ``not_found``
(the observation classifies an explicit, provable absence); every other
sealed path reports truth_state ``sealed``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from resultseal.errors import InvalidArgumentError
from resultseal.models import (
    ClaimType,
    Contract,
    Decision,
    FreshnessMode,
    ObservationEnvelope,
    TransportState,
    TruthState,
)

_RUN_RE = re.compile(r"\d+|\D+")

_SEALED_CODES: tuple[str, ...] = ("SEALED_WITH_REQUIRED_EVIDENCE",)


@dataclass(frozen=True)
class ReferenceClock:
    """Injected notion of 'now'; must be timezone-aware."""

    now: datetime

    def __post_init__(self) -> None:
        if self.now.tzinfo is None:
            raise InvalidArgumentError("ReferenceClock.now must be timezone-aware")


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    truth_state: TruthState
    reason_codes: tuple[str, ...]


def format_clock(now: datetime) -> str:
    """Canonical instant rendering: UTC, second precision, ``Z`` suffix."""
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate(
    envelope: ObservationEnvelope,
    payload: object,
    contract: Contract,
    clock: ReferenceClock,
) -> Evaluation:
    """Decide whether *payload* may support the contract's claim. Pure."""
    if envelope.transport_state in (TransportState.ATTEMPTED, TransportState.DISPATCHED):
        return Evaluation(Decision.BLOCKED, TruthState.UNKNOWN, ("NO_DISPATCH",))
    if envelope.transport_state is TransportState.TRANSPORT_ERROR:
        # Nothing was observed, so the truthful classification is unknown;
        # the failing layer is recorded via the reason code.
        return Evaluation(Decision.BLOCKED, TruthState.UNKNOWN, ("TRANSPORT_FAILED",))
    if envelope.truth_state is TruthState.PARSE_ERROR:
        return Evaluation(Decision.BLOCKED, TruthState.PARSE_ERROR, ("PARSE_FAILED",))
    if envelope.metadata.get("protocol_conflict") is True:
        # e.g. an MCP result carrying isError=true alongside success-shaped
        # content: the source contradicts itself, so nothing may be promoted.
        return Evaluation(
            Decision.BLOCKED, TruthState.UNKNOWN, ("PROTOCOL_CONFLICT",)
        )

    sentinel_matched = _sentinel_matched(payload, contract.not_found_sentinel)
    if contract.claim_type is ClaimType.NOT_FOUND and not sentinel_matched:
        return Evaluation(
            Decision.BLOCKED,
            TruthState.EMPTY if _unusable(payload) else TruthState.OBSERVED,
            ("EMPTY_WITHOUT_NOT_FOUND_SENTINEL",),
        )
    if _unusable(payload) and not sentinel_matched:
        return Evaluation(
            Decision.BLOCKED,
            TruthState.EMPTY,
            ("EMPTY_WITHOUT_NOT_FOUND_SENTINEL",),
        )

    codes: list[str] = []
    if envelope.source_ref != contract.source_ref:
        codes.append("SOURCE_MISMATCH")
    if envelope.target_ref != contract.target_ref:
        codes.append("TARGET_MISMATCH")
    if codes:
        # Identity mismatches classify as source_mismatch (the only identity
        # truth state in the v1 vocabulary); the failing legs appear verbatim
        # in reason codes.
        return Evaluation(Decision.BLOCKED, TruthState.SOURCE_MISMATCH, tuple(codes))

    stale_reason = _freshness_failure(envelope, contract, clock)
    if stale_reason is not None:
        return stale_reason

    missing = [
        name
        for name in contract.required_fields
        if not isinstance(payload, dict) or name not in payload
    ]
    if missing:
        return Evaluation(Decision.BLOCKED, TruthState.PARTIAL, ("MISSING_REQUIRED_FIELD",))

    if (
        contract.claim_type in (ClaimType.EFFECT_OBSERVED, ClaimType.TASK_COMPLETE)
        and contract.effect_evidence_required
        and not envelope.evidence_refs
    ):
        return Evaluation(
            Decision.BLOCKED, TruthState.UNVERIFIED_EFFECT, ("UNVERIFIED_EFFECT",)
        )

    if contract.claim_type is ClaimType.NOT_FOUND:
        return Evaluation(Decision.SEALED, TruthState.NOT_FOUND, _SEALED_CODES)
    return Evaluation(Decision.SEALED, TruthState.SEALED, _SEALED_CODES)


def natural_compare(left: str, right: str) -> int:
    """Natural ordering: digit runs compare numerically, text lexicographically.

    First differing run decides; a proper prefix orders before its extension;
    digit runs equal in value compare equal regardless of leading zeros.
    """
    left_runs = _RUN_RE.findall(left)
    right_runs = _RUN_RE.findall(right)
    for run_left, run_right in zip(left_runs, right_runs, strict=False):
        if run_left.isdigit() and run_right.isdigit():
            as_int_left, as_int_right = int(run_left), int(run_right)
            if as_int_left != as_int_right:
                return -1 if as_int_left < as_int_right else 1
        elif run_left != run_right:
            return -1 if run_left < run_right else 1
    if len(left_runs) != len(right_runs):
        return -1 if len(left_runs) < len(right_runs) else 1
    return 0


def _unusable(payload: object) -> bool:
    return payload is None or payload == "" or payload == {} or payload == []


def _sentinel_matched(payload: object, sentinel: str | None) -> bool:
    if sentinel is None:
        return False
    if payload == sentinel:
        return True
    return isinstance(payload, dict) and any(v == sentinel for v in payload.values())


def _freshness_failure(
    envelope: ObservationEnvelope, contract: Contract, clock: ReferenceClock
) -> Evaluation | None:
    if contract.freshness_mode is FreshnessMode.SOURCE_VERSION:
        if not envelope.source_version:
            return Evaluation(
                Decision.BLOCKED,
                TruthState.UNKNOWN,
                ("MISSING_REQUIRED_FIELD", "STALE_OBSERVATION"),
            )
        assert contract.min_source_version is not None  # guaranteed by Contract
        if natural_compare(envelope.source_version, contract.min_source_version) < 0:
            return Evaluation(
                Decision.BLOCKED, TruthState.STALE, ("STALE_OBSERVATION",)
            )
        return None
    if contract.freshness_mode is FreshnessMode.MAX_AGE_SECONDS:
        observed = _parse_timestamp(envelope.observed_at)
        if observed is None:
            return Evaluation(
                Decision.BLOCKED, TruthState.UNKNOWN, ("SCHEMA_INVALID",)
            )
        assert contract.max_age_seconds is not None  # guaranteed by Contract
        age = (clock.now - observed).total_seconds()
        if age < 0 or age > contract.max_age_seconds:
            return Evaluation(
                Decision.BLOCKED, TruthState.STALE, ("STALE_OBSERVATION",)
            )
    return None


def _parse_timestamp(value: str) -> datetime | None:
    """None unless *value* is an offset-aware ISO-8601 timestamp.

    A naive timestamp cannot be compared to the timezone-aware reference
    clock and is refused like an unparseable one rather than silently
    assumed to be UTC.
    """
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed
