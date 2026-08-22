"""stdio adapter tests: exit code is process completion, nothing more."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from resultseal.errors import SchemaInvalidError
from resultseal.models import TransportState, TruthState
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))


def stdio(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "kind": "stdio",
        "source_ref": "fixture://task",
        "target_ref": "customer:42",
        "exit_code": 0,
        "stdout": '{"status": "done"}',
    }
    base.update(overrides)
    return base


def test_zero_exit_is_process_completion_only() -> None:
    result = normalize(stdio(), CLOCK)
    assert result.envelope.transport_state is TransportState.TRANSPORTED
    assert result.envelope.truth_state is TruthState.OBSERVED
    # Without output_format=json, stdout stays an opaque string payload.
    assert result.payload == '{"status": "done"}'


@pytest.mark.parametrize("exit_code", [1, 2, 127])
def test_nonzero_exit_is_transport_error(exit_code: int) -> None:
    result = normalize(stdio(exit_code=exit_code), CLOCK)
    assert result.envelope.transport_state is TransportState.TRANSPORT_ERROR
    assert result.envelope.truth_state is TruthState.UNKNOWN


def test_missing_stdout_is_unusable_payload() -> None:
    result = normalize(stdio(stdout=None), CLOCK)
    assert result.envelope.transport_state is TransportState.TRANSPORTED
    assert result.payload is None


def test_plain_text_stdout_stays_string_payload() -> None:
    result = normalize(stdio(stdout="done, no json"), CLOCK)
    assert result.payload == "done, no json"


def test_json_output_format_parses_stdout() -> None:
    result = normalize(stdio(output_format="json", stdout='{"ok": true}'), CLOCK)
    assert result.payload == {"ok": True}


def test_json_output_format_with_broken_stdout_is_parse_error() -> None:
    result = normalize(stdio(output_format="json", stdout="{nope"), CLOCK)
    assert result.envelope.truth_state is TruthState.PARSE_ERROR


def test_missing_exit_code_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        normalize({k: v for k, v in stdio().items() if k != "exit_code"}, CLOCK)


def test_command_identity_carried() -> None:
    result = normalize(stdio(command="update-customer"), CLOCK)
    assert result.envelope.metadata.get("command") == "update-customer"
