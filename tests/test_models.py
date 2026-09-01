"""Phase 2 model tests: enum exhaustiveness, strictness, serialization, bounds."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from resultseal.errors import ContractInvalidError, SchemaInvalidError
from resultseal.models import (
    ClaimType,
    Contract,
    Decision,
    FreshnessMode,
    ObservationEnvelope,
    TransportState,
    TruthState,
)

HASH = "sha256:" + "0" * 64


def envelope_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "observation_id": "obs-1",
        "tool_call_id": "call-1",
        "tool_name": "lookup_customer",
        "target_ref": "customer:42",
        "transport_state": TransportState.TRANSPORTED,
        "truth_state": TruthState.OBSERVED,
        "source_ref": "fixture://directory",
        "observed_at": "2026-08-21T10:00:00Z",
        "content_hash": HASH,
    }
    base.update(overrides)
    return base


def envelope(**overrides: object) -> ObservationEnvelope:
    return ObservationEnvelope(**envelope_kwargs(**overrides))  # type: ignore[arg-type]


def contract_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "claim_type": ClaimType.READ_COMPLETE,
        "required_fields": ("customer_id", "name", "email"),
        "freshness_mode": FreshnessMode.SOURCE_VERSION,
        "max_age_seconds": None,
        "min_source_version": "revision-17",
        "source_ref": "fixture://directory",
        "target_ref": "customer:42",
        "not_found_sentinel": None,
        "effect_evidence_required": False,
    }
    base.update(overrides)
    return base


def contract(**overrides: object) -> Contract:
    return Contract(**contract_kwargs(**overrides))  # type: ignore[arg-type]


def test_transport_states_exhaustive() -> None:
    assert {s.value for s in TransportState} == {
        "attempted",
        "dispatched",
        "transported",
        "transport_error",
    }


def test_truth_states_exhaustive() -> None:
    assert {s.value for s in TruthState} == {
        "observed",
        "complete",
        "empty",
        "not_found",
        "partial",
        "stale",
        "source_mismatch",
        "unverified_effect",
        "parse_error",
        "unknown",
        "sealed",
    }


def test_claim_types_exhaustive() -> None:
    assert {c.value for c in ClaimType} == {
        "found",
        "not_found",
        "read_complete",
        "effect_observed",
        "task_complete",
    }


def test_decision_values() -> None:
    assert {d.value for d in Decision} == {"sealed", "blocked"}


def test_unknown_enum_rejected() -> None:
    with pytest.raises(ValueError):
        TransportState("teleported")


def test_envelope_frozen() -> None:
    env = envelope()
    with pytest.raises(FrozenInstanceError):
        env.tool_name = "other"  # type: ignore[misc]


def test_envelope_metadata_is_immutable_mapping_proxy() -> None:
    raw_meta = {"key": "value"}
    e = envelope(metadata=raw_meta)
    assert isinstance(e.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        e.metadata["key"] = "new_value"  # type: ignore[index]


def test_envelope_roundtrip_json() -> None:
    env = envelope(evidence_refs=("e1",), reason_codes=("SEALED_WITH_REQUIRED_EVIDENCE",))
    encoded = json.dumps(env.to_dict())
    restored = ObservationEnvelope.from_dict(json.loads(encoded))
    assert restored == env


def test_envelope_rejects_missing_field() -> None:
    raw = envelope_kwargs()
    del raw["content_hash"]
    with pytest.raises(SchemaInvalidError) as excinfo:
        ObservationEnvelope.from_dict(raw)
    assert "content_hash" in str(excinfo.value)


def test_envelope_rejects_unknown_field() -> None:
    raw = envelope_kwargs(surprise="x")
    with pytest.raises(SchemaInvalidError):
        ObservationEnvelope.from_dict(raw)


def test_envelope_rejects_unknown_enum_string() -> None:
    raw = envelope_kwargs()
    raw["transport_state"] = "teleported"
    with pytest.raises(SchemaInvalidError):
        ObservationEnvelope.from_dict(raw)


def test_envelope_rejects_bad_content_hash() -> None:
    with pytest.raises(SchemaInvalidError):
        envelope(content_hash="md5:abc")


def test_envelope_rejects_bad_reason_code() -> None:
    with pytest.raises(SchemaInvalidError):
        envelope(reason_codes=("not_upper",))


def test_envelope_rejects_oversized_field() -> None:
    with pytest.raises(SchemaInvalidError):
        envelope(tool_name="t" * 257)


def test_envelope_rejects_nonscalar_metadata() -> None:
    with pytest.raises(SchemaInvalidError):
        envelope(metadata={"nested": {"a": 1}})


def test_envelope_rejects_oversized_evidence_list() -> None:
    with pytest.raises(SchemaInvalidError):
        envelope(evidence_refs=tuple(f"e{i}" for i in range(65)))


def test_contract_roundtrip_json() -> None:
    c = contract(not_found_sentinel="NOT_FOUND")
    restored = Contract.from_dict(json.loads(json.dumps(c.to_dict())))
    assert restored == c


def test_contract_rejects_unknown_key() -> None:
    raw = contract().to_dict()
    raw["policy"] = "extra"
    with pytest.raises(ContractInvalidError):
        Contract.from_dict(raw)


def test_contract_rejects_missing_key() -> None:
    raw = contract().to_dict()
    del raw["required_fields"]
    with pytest.raises(ContractInvalidError):
        Contract.from_dict(raw)


def test_contract_rejects_bad_claim() -> None:
    with pytest.raises(ContractInvalidError):
        contract(claim_type="omniscient")  # type: ignore[arg-type]


def test_contract_rejects_oversized_required_fields() -> None:
    with pytest.raises(ContractInvalidError):
        contract(required_fields=tuple(f"f{i}" for i in range(65)))


def test_contract_rejects_max_age_out_of_range() -> None:
    with pytest.raises(ContractInvalidError):
        contract(freshness_mode=FreshnessMode.MAX_AGE_SECONDS, max_age_seconds=31_536_001)


def test_contract_rejects_mismatched_freshness_fields() -> None:
    with pytest.raises(ContractInvalidError):
        contract(freshness_mode=FreshnessMode.MAX_AGE_SECONDS, max_age_seconds=None)
