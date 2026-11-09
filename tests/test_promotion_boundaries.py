"""Regression cases that previously promoted invalid observations to sealed."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import resultseal
from resultseal.cli import main
from resultseal.errors import LimitExceededError, SchemaInvalidError
from resultseal.limits import Limits

NOW = datetime(2026, 11, 9, tzinfo=UTC)
CONTRACT_DATA = {
    "schema_version": "1",
    "claim_type": "found",
    "required_fields": [],
    "freshness": {"mode": "not_required"},
    "source_ref": "s",
    "target_ref": "t",
}
CONTRACT = resultseal.load_contract(CONTRACT_DATA)


def observation(kind: str, body: object) -> dict[str, object]:
    raw = {"kind": kind, "source_ref": "s", "target_ref": "t"}
    if kind == "stdio":
        return {**raw, "exit_code": 0, "output_format": "json", "stdout": body}
    return {**raw, "status_code": 200, "body": body}


@pytest.mark.parametrize("kind", ["json", "http_json", "stdio"])
@pytest.mark.parametrize(
    "body",
    ["[" * 40 + "1" + "]" * 40, "[" * 1500 + "1" + "]" * 1500, "[" + "0," * 4096 + "0]"],
    ids=["depth", "parser-recursion", "nodes"],
)
def test_nested_json_is_bounded_before_promotion(kind: str, body: str) -> None:
    with pytest.raises(LimitExceededError):
        resultseal.seal(observation(kind, body), CONTRACT, now=NOW)


@pytest.mark.parametrize("kind", ["json", "http_json", "stdio"])
@pytest.mark.parametrize("body", ["NaN", "Infinity", "-Infinity", "1e999", '{"n": NaN}'])
def test_non_finite_nested_json_cannot_seal(kind: str, body: str) -> None:
    if body == "1e999":
        with pytest.raises(SchemaInvalidError, match="finite"):
            resultseal.check(observation(kind, body), CONTRACT, now=NOW)
        return
    result = resultseal.check(observation(kind, body), CONTRACT, now=NOW)
    assert not result.sealed
    assert result.reason_codes == ("PARSE_FAILED",)


@pytest.mark.parametrize("payload", [{"id": 1}, "answer text", [1]])
def test_mcp_schema_required_fields_prevent_sealing(payload: object) -> None:
    raw = {
        "kind": "mcp",
        "source_ref": "s",
        "target_ref": "t",
        "structuredContent": payload,
        "outputSchema": {"required": ["id", "name"]},
    }
    result = resultseal.check(raw, CONTRACT, now=NOW)
    assert not result.sealed
    assert result.truth_state is resultseal.TruthState.PARTIAL
    assert result.reason_codes == ("MISSING_REQUIRED_FIELD",)


def test_explicit_null_timestamp_is_not_replaced_by_now() -> None:
    contract = resultseal.load_contract(
        {
            **CONTRACT_DATA,
            "freshness": {"mode": "max_age_seconds", "max_age_seconds": 60},
        }
    )
    raw = {**observation("json", {"id": 1}), "observed_at": None}
    with pytest.raises(SchemaInvalidError):
        resultseal.seal(raw, contract, now=NOW)


@pytest.mark.parametrize(
    "limits", [Limits(max_nodes=1), Limits(max_depth=1), Limits(max_string_chars=2)]
)
def test_contract_mapping_respects_input_limits(limits: Limits) -> None:
    with pytest.raises(LimitExceededError):
        resultseal.load_contract(CONTRACT_DATA, limits=limits)


@pytest.mark.parametrize(
    "raw",
    [
        observation("json", {"name": "\ud800"}),
        observation("json", '{"name":"\\ud800"}'),
        observation("stdio", '{"\\udfff":1}'),
        {**observation("json", {"id": 1}), "source_ref": "\ud800"},
    ],
    ids=["body", "nested-body", "nested-key", "identity"],
)
def test_invalid_unicode_cannot_be_promoted(raw: dict[str, object]) -> None:
    with pytest.raises(SchemaInvalidError):
        resultseal.seal(raw, CONTRACT, now=NOW)


@pytest.mark.parametrize(
    ("raw", "exit_code", "reason"),
    [
        (observation("json", "[" * 40 + "1" + "]" * 40), 3, "LIMIT_EXCEEDED"),
        (observation("json", {"name": "\ud800"}), 2, "SCHEMA_INVALID"),
        ({**observation("json", {"id": 1}), "observed_at": None}, 2, "SCHEMA_INVALID"),
        (
            {
                "kind": "mcp",
                "source_ref": "s",
                "target_ref": "t",
                "structuredContent": {"id": 1},
                "outputSchema": {"required": ["name"]},
            },
            1,
            "MISSING_REQUIRED_FIELD",
        ),
    ],
    ids=["nested-limit", "invalid-unicode", "null-timestamp", "mcp-partial"],
)
def test_cli_reports_promotion_boundary_failures(
    raw: dict[str, object],
    exit_code: int,
    reason: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    response = tmp_path / "response.json"
    contract = tmp_path / "contract.json"
    response.write_text(json.dumps(raw), encoding="utf-8")
    contract.write_text(json.dumps(CONTRACT_DATA), encoding="utf-8")
    assert main(["check", str(response), "--contract", str(contract)]) == exit_code
    captured = capsys.readouterr()
    if exit_code == 1:
        record = json.loads(captured.out)
        assert record["decision"] == "blocked"
        assert record["reason_codes"] == [reason]
    else:
        assert reason in captured.err
        assert not captured.out
