"""Public high-level API: check / seal / load_contract agree with the CLI pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import resultseal
from resultseal import BlockedObservation, Decision, TruthState
from resultseal.cli import main
from resultseal.errors import (
    InvalidArgumentError,
    LimitExceededError,
    ResultSealError,
    SchemaInvalidError,
)
from resultseal.fixtures import expectation_matches, load_fixture_file
from resultseal.limits import Limits
from resultseal.report import render_json
from resultseal.rules import Evaluation

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"
FIXTURES = REPO_ROOT / "fixtures"
NOW = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)

CONTRACT = resultseal.load_contract(EXAMPLES / "customer_contract.json")


def _customer(body: object) -> dict[str, object]:
    return {
        "kind": "json",
        "source_ref": "mcp://crm-server",
        "target_ref": "customer:42",
        "body": body,
    }


def test_seal_returns_the_verified_payload() -> None:
    record = {"customer_id": "42", "name": "Ada"}
    assert resultseal.seal(_customer(record), CONTRACT, now=NOW) == record


def test_seal_raises_with_reason_codes_when_blocked() -> None:
    with pytest.raises(BlockedObservation, match="EMPTY_WITHOUT_NOT_FOUND_SENTINEL") as info:
        resultseal.seal(_customer([]), CONTRACT, now=NOW)
    assert info.value.reason_codes == ("EMPTY_WITHOUT_NOT_FOUND_SENTINEL",)
    assert info.value.result.truth_state is TruthState.EMPTY


def test_blocked_observation_is_not_an_input_error() -> None:
    assert not issubclass(BlockedObservation, ResultSealError)


def test_check_returns_blocked_results_instead_of_raising() -> None:
    result = resultseal.check(_customer({"customer_id": "42"}), CONTRACT, now=NOW)
    assert not result.sealed
    assert result.decision is Decision.BLOCKED
    assert result.truth_state is TruthState.PARTIAL
    assert result.reason_codes == ("MISSING_REQUIRED_FIELD",)


def test_check_rejects_non_mapping_input() -> None:
    with pytest.raises(SchemaInvalidError):
        resultseal.check([], CONTRACT, now=NOW)  # type: ignore[arg-type]


def test_check_requires_timezone_aware_now() -> None:
    with pytest.raises(InvalidArgumentError):
        resultseal.check(_customer([]), CONTRACT, now=datetime(2026, 1, 1))


def test_check_enforces_input_limits() -> None:
    nested: object = {}
    for _ in range(40):
        nested = {"n": nested}
    with pytest.raises(LimitExceededError):
        resultseal.check(_customer(nested), CONTRACT, now=NOW)
    relaxed = Limits(max_depth=64)
    assert not resultseal.check(_customer(nested), CONTRACT, now=NOW, limits=relaxed).sealed


def test_load_contract_accepts_paths_and_mappings() -> None:
    path = EXAMPLES / "customer_contract.json"
    from_mapping = resultseal.load_contract(json.loads(path.read_text(encoding="utf-8")))
    assert resultseal.load_contract(str(path)) == from_mapping == CONTRACT


@pytest.mark.parametrize("example", ["mcp_result.json", "http_empty.json"])
def test_record_is_byte_identical_to_cli_json(
    example: str, capsys: pytest.CaptureFixture[str]
) -> None:
    path = EXAMPLES / example
    main(["check", str(path), "--contract", str(EXAMPLES / "customer_contract.json"),
          "--now", "2026-08-21T12:00:00Z"])
    cli_output = capsys.readouterr().out.strip()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert render_json(resultseal.check(raw, CONTRACT, now=NOW).record()) == cli_output


@pytest.mark.parametrize(
    "path",
    [p for p in sorted(FIXTURES.glob("*.yaml")) if p.name != "unsafe-input.yaml"],
    ids=lambda p: p.name,
)
def test_api_meets_every_fixture_expectation(path: Path) -> None:
    bundle = load_fixture_file(path, Limits())
    assert bundle.contract is not None
    result = resultseal.check(bundle.raw_input, bundle.contract, now=NOW)
    evaluation = Evaluation(result.decision, result.truth_state, result.reason_codes)
    assert expectation_matches(bundle.expected, evaluation)


def test_public_names_resolve() -> None:
    for name in resultseal.__all__:
        assert hasattr(resultseal, name), name
