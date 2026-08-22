"""HTTP/JSON adapter tests: transport facts only, never semantic truth."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from resultseal.errors import SchemaInvalidError
from resultseal.models import TransportState, TruthState
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))


def http(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "kind": "http_json",
        "status_code": 200,
        "source_ref": "fixture://directory",
        "target_ref": "customer:42",
        "body": {"customer_id": "42"},
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("status", [200, 201, 204, 302])
def test_2xx_3xx_is_only_transported(status: int) -> None:
    result = normalize(http(status_code=status), CLOCK)
    assert result.envelope.transport_state is TransportState.TRANSPORTED
    assert result.envelope.truth_state is TruthState.OBSERVED
    # A 200 with a full-looking body must NOT be complete/sealed on its own.
    assert result.envelope.truth_state is not TruthState.COMPLETE


@pytest.mark.parametrize("status", [400, 404, 500, 503])
def test_4xx_5xx_is_transport_error(status: int) -> None:
    result = normalize(http(status_code=status), CLOCK)
    assert result.envelope.transport_state is TransportState.TRANSPORT_ERROR
    assert result.envelope.truth_state is TruthState.UNKNOWN


def test_empty_body_is_unusable_payload_not_not_found() -> None:
    result = normalize(http(body=""), CLOCK)
    assert result.envelope.transport_state is TransportState.TRANSPORTED
    assert result.payload is None


def test_json_string_body_parses() -> None:
    result = normalize(http(body='{"a": 1}'), CLOCK)
    assert result.payload == {"a": 1}


def test_malformed_body_is_parse_error_envelope() -> None:
    result = normalize(http(body="{broken"), CLOCK)
    assert result.envelope.truth_state is TruthState.PARSE_ERROR
    assert result.envelope.transport_state is TransportState.TRANSPORTED
    assert result.payload is None


def test_missing_status_code_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        normalize({k: v for k, v in http().items() if k != "status_code"}, CLOCK)


def test_non_integer_status_code_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        normalize(http(status_code="200"), CLOCK)


def test_source_version_carried_into_envelope() -> None:
    result = normalize(http(source_version="revision-17"), CLOCK)
    assert result.envelope.source_version == "revision-17"


def test_request_target_used_as_target_ref() -> None:
    raw = http()
    del raw["target_ref"]
    raw["request_target"] = "customer:42"
    result = normalize(raw, CLOCK)
    assert result.envelope.target_ref == "customer:42"


def test_response_target_wins_over_request_target() -> None:
    raw = http()
    del raw["target_ref"]
    raw["request_target"] = "customer:41"
    raw["response_target"] = "customer:42"
    assert normalize(raw, CLOCK).envelope.target_ref == "customer:42"


def test_http_without_any_target_rejected() -> None:
    raw = {k: v for k, v in http().items() if k != "target_ref"}
    with pytest.raises(SchemaInvalidError):
        normalize(raw, CLOCK)
