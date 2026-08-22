"""MCP-style adapter tests: structuredContent, outputSchema, isError conflicts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from resultseal.errors import SchemaInvalidError
from resultseal.models import TransportState, TruthState
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))


def mcp(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "kind": "mcp",
        "source_ref": "fixture://directory",
        "target_ref": "customer:42",
        "structuredContent": {"customer_id": "42", "name": "Ada"},
    }
    base.update(overrides)
    return base


def test_structured_content_is_payload() -> None:
    result = normalize(mcp(), CLOCK)
    assert result.payload == {"customer_id": "42", "name": "Ada"}
    assert result.envelope.transport_state is TransportState.TRANSPORTED


def test_empty_structured_object_is_not_not_found() -> None:
    result = normalize(mcp(structuredContent={}), CLOCK)
    assert result.envelope.truth_state is TruthState.OBSERVED
    assert result.payload == {}  # rules classify it empty; adapter does not


def test_is_error_conflict_marks_protocol_conflict() -> None:
    result = normalize(
        mcp(structuredContent={"status": "updated"}, isError=True), CLOCK
    )
    assert result.envelope.metadata.get("protocol_conflict") is True
    # The envelope stays structural; the rules engine blocks on the conflict.


def test_is_error_false_is_not_a_conflict() -> None:
    result = normalize(mcp(isError=False), CLOCK)
    assert "protocol_conflict" not in result.envelope.metadata


def test_output_schema_missing_fields_recorded() -> None:
    result = normalize(
        mcp(outputSchema={"required": ["customer_id", "name", "email"]}), CLOCK
    )
    assert result.envelope.metadata.get("missing_schema_fields") == "email"


def test_output_schema_all_present_records_nothing() -> None:
    result = normalize(
        mcp(outputSchema={"required": ["customer_id"]}), CLOCK
    )
    assert "missing_schema_fields" not in result.envelope.metadata


def test_text_content_fallback() -> None:
    result = normalize(mcp(structuredContent=None, text="plain answer"), CLOCK)
    assert result.payload == "plain answer"


def test_missing_source_rejected() -> None:
    raw = mcp()
    del raw["source_ref"]
    with pytest.raises(SchemaInvalidError):
        normalize(raw, CLOCK)
