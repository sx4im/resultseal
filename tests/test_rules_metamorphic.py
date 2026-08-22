"""Metamorphic properties of the rules engine (PROMOTION_RULES test obligations)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from resultseal.models import (
    ClaimType,
    Contract,
    Decision,
    FreshnessMode,
    ObservationEnvelope,
    TransportState,
    TruthState,
)
from resultseal.rules import ReferenceClock, evaluate

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))
HASH = "sha256:" + "0" * 64
FULL = {"customer_id": "42", "name": "Ada", "email": "ada@example.test"}


def envelope(**overrides: object) -> ObservationEnvelope:
    base: dict[str, object] = {
        "observation_id": "obs-m",
        "tool_call_id": "call-m",
        "tool_name": "lookup_customer",
        "target_ref": "customer:42",
        "transport_state": TransportState.TRANSPORTED,
        "truth_state": TruthState.OBSERVED,
        "source_ref": "fixture://directory",
        "observed_at": "2026-08-21T10:00:00Z",
        "content_hash": HASH,
    }
    base.update(overrides)
    return ObservationEnvelope(**base)  # type: ignore[arg-type]


SEALED_CASES: tuple[tuple[ObservationEnvelope, object, Contract], ...] = (
    (
        envelope(source_version="revision-17"),
        FULL,
        Contract(
            claim_type=ClaimType.READ_COMPLETE,
            required_fields=("customer_id", "name", "email"),
            freshness_mode=FreshnessMode.SOURCE_VERSION,
            max_age_seconds=None,
            min_source_version="revision-17",
            source_ref="fixture://directory",
            target_ref="customer:42",
        ),
    ),
    (
        envelope(evidence_refs=("readback:1",)),
        {"status": "updated"},
        Contract(
            claim_type=ClaimType.EFFECT_OBSERVED,
            required_fields=("status",),
            freshness_mode=FreshnessMode.NOT_REQUIRED,
            max_age_seconds=None,
            min_source_version=None,
            source_ref="fixture://directory",
            target_ref="customer:42",
            effect_evidence_required=True,
        ),
    ),
    (
        envelope(observed_at="2026-08-21T11:00:00Z"),
        FULL,
        Contract(
            claim_type=ClaimType.FOUND,
            required_fields=("customer_id",),
            freshness_mode=FreshnessMode.MAX_AGE_SECONDS,
            max_age_seconds=7200,
            min_source_version=None,
            source_ref="fixture://directory",
            target_ref="customer:42",
        ),
    ),
)


def is_sealed(case: tuple[ObservationEnvelope, object, Contract]) -> bool:
    env_obj, payload, contract = case
    return evaluate(env_obj, payload, contract, CLOCK).decision is Decision.SEALED


def test_all_seed_cases_seal() -> None:
    assert len(SEALED_CASES) == 3
    for case in SEALED_CASES:
        assert is_sealed(case), case


def test_removing_evidence_cannot_improve_a_decision() -> None:
    for env_obj, payload, contract in SEALED_CASES:
        stripped = replace(env_obj, evidence_refs=())
        result = evaluate(stripped, payload, contract, CLOCK)
        if not contract.effect_evidence_required:
            continue  # evidence was not load-bearing for this claim class
        assert result.decision is Decision.BLOCKED
        assert result.reason_codes == ("UNVERIFIED_EFFECT",)


def test_target_change_breaks_any_seal() -> None:
    for env_obj, payload, contract in SEALED_CASES:
        moved = replace(env_obj, target_ref="customer:999999")
        result = evaluate(moved, payload, contract, CLOCK)
        assert result.decision is Decision.BLOCKED
        assert result.reason_codes == ("TARGET_MISMATCH",)


def test_older_revision_breaks_freshness() -> None:
    for env_obj, payload, contract in SEALED_CASES:
        if contract.freshness_mode is not FreshnessMode.SOURCE_VERSION:
            continue
        aged = replace(env_obj, source_version="revision-1")
        result = evaluate(aged, payload, contract, CLOCK)
        assert result.decision is Decision.BLOCKED
        assert result.reason_codes == ("STALE_OBSERVATION",)


def test_weakening_the_contract_never_unblocks_a_blocked_case() -> None:
    blocked_cases: tuple[tuple[ObservationEnvelope, object, Contract], ...] = (
        (envelope(transport_state=TransportState.ATTEMPTED), FULL, SEALED_CASES[0][2]),
        (envelope(transport_state=TransportState.TRANSPORT_ERROR), None, SEALED_CASES[0][2]),
        (envelope(), "", SEALED_CASES[0][2]),
    )
    for env_obj, payload, contract in blocked_cases:
        weakened = Contract(
            claim_type=contract.claim_type,
            required_fields=(),
            freshness_mode=FreshnessMode.NOT_REQUIRED,
            max_age_seconds=None,
            min_source_version=None,
            source_ref=contract.source_ref,
            target_ref=contract.target_ref,
        )
        result = evaluate(env_obj, payload, weakened, CLOCK)
        assert result.decision is Decision.BLOCKED
