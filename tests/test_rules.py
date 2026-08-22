"""Phase 3 promotion-rule tests: one per precedence row, plus comparator."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
from resultseal.rules import ReferenceClock, evaluate, natural_compare

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))


def env(**overrides: object) -> ObservationEnvelope:
    base: dict[str, object] = {
        "observation_id": "obs-1",
        "tool_call_id": "call-1",
        "tool_name": "lookup_customer",
        "target_ref": "customer:42",
        "transport_state": TransportState.TRANSPORTED,
        "truth_state": TruthState.OBSERVED,
        "source_ref": "fixture://directory",
        "observed_at": "2026-08-21T10:00:00Z",
        "content_hash": "sha256:" + "0" * 64,
    }
    base.update(overrides)
    return ObservationEnvelope(**base)  # type: ignore[arg-type]


FULL = {"customer_id": "42", "name": "Ada", "email": "ada@example.test"}


def read_contract(**overrides: object) -> Contract:
    base: dict[str, object] = {
        "claim_type": ClaimType.READ_COMPLETE,
        "required_fields": ("customer_id", "name", "email"),
        "freshness_mode": FreshnessMode.SOURCE_VERSION,
        "max_age_seconds": None,
        "min_source_version": "revision-17",
        "source_ref": "fixture://directory",
        "target_ref": "customer:42",
    }
    base.update(overrides)
    return Contract(**base)  # type: ignore[arg-type]


def test_no_dispatch_blocks_even_with_perfect_payload() -> None:
    result = evaluate(env(transport_state=TransportState.ATTEMPTED), FULL, read_contract(), CLOCK)
    assert result.decision is Decision.BLOCKED
    assert result.truth_state is TruthState.UNKNOWN
    assert result.reason_codes == ("NO_DISPATCH",)


def test_transport_error_blocks() -> None:
    result = evaluate(
        env(transport_state=TransportState.TRANSPORT_ERROR), None, read_contract(), CLOCK
    )
    assert result.truth_state is TruthState.UNKNOWN
    assert result.reason_codes == ("TRANSPORT_FAILED",)


def test_parse_error_blocks() -> None:
    result = evaluate(env(truth_state=TruthState.PARSE_ERROR), None, read_contract(), CLOCK)
    assert result.truth_state is TruthState.PARSE_ERROR
    assert result.reason_codes == ("PARSE_FAILED",)


def test_protocol_conflict_blocks() -> None:
    result = evaluate(
        env(metadata={"protocol_conflict": True}), FULL, read_contract(), CLOCK
    )
    assert result.decision is Decision.BLOCKED
    assert result.truth_state is TruthState.UNKNOWN
    assert result.reason_codes == ("PROTOCOL_CONFLICT",)


@pytest.mark.parametrize("payload", [None, "", {}, []])
def test_empty_payload_without_sentinel_blocks(payload: object) -> None:
    result = evaluate(env(), payload, read_contract(), CLOCK)
    assert result.truth_state is TruthState.EMPTY
    assert result.reason_codes == ("EMPTY_WITHOUT_NOT_FOUND_SENTINEL",)
    assert result.decision is Decision.BLOCKED


def test_empty_is_never_not_found() -> None:
    contract = read_contract(
        claim_type=ClaimType.NOT_FOUND,
        required_fields=(),
        not_found_sentinel="NOT_FOUND",
    )
    result = evaluate(env(), "", contract, CLOCK)
    assert result.truth_state is TruthState.EMPTY
    assert result.decision is Decision.BLOCKED


def test_explicit_sentinel_seals_not_found() -> None:
    contract = read_contract(
        claim_type=ClaimType.NOT_FOUND,
        required_fields=(),
        freshness_mode=FreshnessMode.NOT_REQUIRED,
        min_source_version=None,
        not_found_sentinel="NOT_FOUND",
    )
    result = evaluate(env(), {"status": "NOT_FOUND"}, contract, CLOCK)
    assert result.decision is Decision.SEALED
    assert result.truth_state is TruthState.NOT_FOUND
    assert result.reason_codes == ("SEALED_WITH_REQUIRED_EVIDENCE",)


def test_sentinel_exact_string_payload_seals() -> None:
    contract = read_contract(
        claim_type=ClaimType.NOT_FOUND,
        required_fields=(),
        freshness_mode=FreshnessMode.NOT_REQUIRED,
        min_source_version=None,
        not_found_sentinel="NOT_FOUND",
    )
    result = evaluate(env(), "NOT_FOUND", contract, CLOCK)
    assert result.decision is Decision.SEALED


def test_sentinel_without_contract_sentinel_falls_through_to_completeness() -> None:
    result = evaluate(
        env(source_version="revision-17"),
        {"status": "NOT_FOUND"},
        read_contract(),
        CLOCK,
    )
    assert result.truth_state is TruthState.PARTIAL
    assert result.reason_codes == ("MISSING_REQUIRED_FIELD",)


def test_source_mismatch_blocks() -> None:
    contract = read_contract(source_ref="fixture://other")
    result = evaluate(env(), FULL, contract, CLOCK)
    assert result.truth_state is TruthState.SOURCE_MISMATCH
    assert result.reason_codes == ("SOURCE_MISMATCH",)


def test_target_mismatch_blocks() -> None:
    contract = read_contract(target_ref="customer:99")
    result = evaluate(env(), FULL, contract, CLOCK)
    assert result.truth_state is TruthState.SOURCE_MISMATCH
    assert result.reason_codes == ("TARGET_MISMATCH",)


def test_double_mismatch_reports_both_codes() -> None:
    contract = read_contract(source_ref="fixture://other", target_ref="customer:99")
    result = evaluate(env(), FULL, contract, CLOCK)
    assert result.reason_codes == ("SOURCE_MISMATCH", "TARGET_MISMATCH")
    assert result.truth_state is TruthState.SOURCE_MISMATCH


def test_stale_takes_precedence_over_partial() -> None:
    result = evaluate(
        env(source_version="revision-1"),
        {"customer_id": "42", "name": "Ada"},
        read_contract(),
        CLOCK,
    )
    assert result.truth_state is TruthState.STALE
    assert result.reason_codes == ("STALE_OBSERVATION",)


def test_missing_source_version_is_unknown() -> None:
    result = evaluate(env(source_version=None), FULL, read_contract(), CLOCK)
    assert result.truth_state is TruthState.UNKNOWN
    assert result.reason_codes == ("MISSING_REQUIRED_FIELD", "STALE_OBSERVATION")


def test_equal_source_version_seals() -> None:
    result = evaluate(env(source_version="revision-17"), FULL, read_contract(), CLOCK)
    assert result.decision is Decision.SEALED
    assert result.truth_state is TruthState.SEALED
    assert result.reason_codes == ("SEALED_WITH_REQUIRED_EVIDENCE",)


def test_partial_blocks_with_missing_required_field() -> None:
    result = evaluate(
        env(source_version="revision-17"), {"customer_id": "42"}, read_contract(), CLOCK
    )
    assert result.truth_state is TruthState.PARTIAL
    assert result.reason_codes == ("MISSING_REQUIRED_FIELD",)


def test_non_dict_payload_with_required_fields_is_partial() -> None:
    result = evaluate(env(source_version="revision-17"), "just text", read_contract(), CLOCK)
    assert result.truth_state is TruthState.PARTIAL


def test_unverified_effect_blocks_without_evidence() -> None:
    contract = read_contract(
        claim_type=ClaimType.EFFECT_OBSERVED,
        required_fields=("status",),
        freshness_mode=FreshnessMode.NOT_REQUIRED,
        min_source_version=None,
        effect_evidence_required=True,
    )
    result = evaluate(env(), {"status": "updated"}, contract, CLOCK)
    assert result.truth_state is TruthState.UNVERIFIED_EFFECT
    assert result.reason_codes == ("UNVERIFIED_EFFECT",)


def test_effect_with_evidence_seals() -> None:
    contract = read_contract(
        claim_type=ClaimType.EFFECT_OBSERVED,
        required_fields=("status",),
        freshness_mode=FreshnessMode.NOT_REQUIRED,
        min_source_version=None,
        effect_evidence_required=True,
    )
    result = evaluate(
        env(evidence_refs=("readback:customer:42",)), {"status": "updated"}, contract, CLOCK
    )
    assert result.decision is Decision.SEALED


def test_task_complete_without_evidence_blocks() -> None:
    contract = read_contract(
        claim_type=ClaimType.TASK_COMPLETE,
        required_fields=(),
        freshness_mode=FreshnessMode.NOT_REQUIRED,
        min_source_version=None,
        effect_evidence_required=True,
    )
    result = evaluate(env(), {"ok": True}, contract, CLOCK)
    assert result.truth_state is TruthState.UNVERIFIED_EFFECT


def test_max_age_stale_blocks() -> None:
    contract = read_contract(
        freshness_mode=FreshnessMode.MAX_AGE_SECONDS,
        min_source_version=None,
        max_age_seconds=600,
    )
    result = evaluate(env(observed_at="2026-08-21T09:00:00Z"), FULL, contract, CLOCK)
    assert result.truth_state is TruthState.STALE


def test_max_age_fresh_seals() -> None:
    contract = read_contract(
        freshness_mode=FreshnessMode.MAX_AGE_SECONDS,
        min_source_version=None,
        max_age_seconds=7200,
    )
    result = evaluate(env(observed_at="2026-08-21T10:00:00Z"), FULL, contract, CLOCK)
    assert result.decision is Decision.SEALED


def test_unparseable_observed_at_with_max_age_is_unknown() -> None:
    contract = read_contract(
        freshness_mode=FreshnessMode.MAX_AGE_SECONDS,
        min_source_version=None,
        max_age_seconds=600,
    )
    result = evaluate(env(observed_at="not-a-timestamp"), FULL, contract, CLOCK)
    assert result.truth_state is TruthState.UNKNOWN
    assert "SCHEMA_INVALID" in result.reason_codes


def test_not_required_freshness_ignores_version() -> None:
    contract = read_contract(
        freshness_mode=FreshnessMode.NOT_REQUIRED, min_source_version=None
    )
    result = evaluate(env(source_version=None), FULL, contract, CLOCK)
    assert result.decision is Decision.SEALED


def test_evaluation_deterministic() -> None:
    first = evaluate(env(), FULL, read_contract(), CLOCK)
    second = evaluate(env(), FULL, read_contract(), CLOCK)
    assert first == second


def test_naive_clock_rejected() -> None:
    with pytest.raises(InvalidArgumentError):
        ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0))


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("revision-1", "revision-17", -1),
        ("revision-9", "revision-17", -1),
        ("revision-17", "revision-17", 0),
        ("revision-2", "revision-10", -1),
        ("v2", "v10", -1),
        ("revision-1", "revision-1-extra", -1),
        ("revision-17", "revision-1", 1),
        ("1", "01", 0),
        ("text-2", "10", 1),
    ],
)
def test_natural_compare(left: str, right: str, expected: int) -> None:
    assert natural_compare(left, right) == expected
    assert natural_compare(right, left) == -expected
