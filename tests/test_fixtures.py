"""Fixture-bundle loading tests: structure, contracts, expectations, safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from resultseal.errors import ContractInvalidError, LimitExceededError
from resultseal.fixtures import FixtureBundle, load_fixture_file
from resultseal.limits import Limits
from resultseal.models import ClaimType, TruthState

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "fixtures"
LIMITS = Limits()

ALL_FIXTURES = sorted(FIXTURES.glob("*.yaml"))


@pytest.mark.parametrize("path", ALL_FIXTURES, ids=lambda p: p.name)
def test_shipped_fixture_loads(path: Path) -> None:
    # unsafe-input.yaml's tag lives inside a quoted scalar, so the *outer*
    # document is safe; its nested YAML payload is rejected during input
    # preparation (kind: yaml), before evaluation — exercised in the
    # normalizer tests.
    bundle = load_fixture_file(path, LIMITS)
    assert bundle.name == path.stem


def test_unsafe_input_fixture_declares_rejection() -> None:
    bundle = load_fixture_file(FIXTURES / "unsafe-input.yaml", LIMITS)
    assert bundle.expected.decision_literal == "rejected"
    assert not bundle.requires_contract()
    assert "UNSAFE_INPUT" in bundle.expected.reason_codes


def test_embedded_contract_present_and_typed() -> None:
    bundle = load_fixture_file(FIXTURES / "complete-fresh-result.yaml", LIMITS)
    assert bundle.contract is not None
    assert bundle.contract.claim_type is ClaimType.READ_COMPLETE
    assert bundle.contract.min_source_version == "revision-17"


def test_contractless_bundle_requires_contract() -> None:
    raw = (
        "fixture_version: 1\n"
        "name: bare\n"
        "input:\n  kind: json\n  body: {}\n"
        "expected:\n  decision: blocked\n"
    )
    bundle = FixtureBundle.loads(raw, LIMITS)
    assert bundle.contract is None
    assert bundle.requires_contract()


def test_expected_truth_state_parsed() -> None:
    bundle = load_fixture_file(FIXTURES / "empty-result.yaml", LIMITS)
    assert bundle.expected.decision_literal == "blocked"
    assert bundle.expected.truth_state is TruthState.EMPTY
    assert bundle.expected.reason_codes == ("EMPTY_WITHOUT_NOT_FOUND_SENTINEL",)


def test_unknown_top_level_key_rejected() -> None:
    raw = (
        "fixture_version: 1\nname: x\nsurprise: 1\n"
        "input: {kind: json}\nexpected: {decision: blocked}\n"
    )
    with pytest.raises(ContractInvalidError):
        FixtureBundle.loads(raw, LIMITS)


def test_bad_decision_literal_rejected() -> None:
    raw = (
        "fixture_version: 1\nname: x\n"
        "input: {kind: json}\nexpected: {decision: maybe}\n"
    )
    with pytest.raises(ContractInvalidError):
        FixtureBundle.loads(raw, LIMITS)


def test_bad_fixture_version_rejected() -> None:
    raw = (
        "fixture_version: 2\nname: x\n"
        "input: {kind: json}\nexpected: {decision: blocked}\n"
    )
    with pytest.raises(ContractInvalidError):
        FixtureBundle.loads(raw, LIMITS)


def test_invalid_embedded_contract_propagates() -> None:
    raw = (
        "fixture_version: 1\nname: x\n"
        "contract: {schema_version: '9', claim_type: found}\n"
        "input: {kind: json}\nexpected: {decision: sealed}\n"
    )
    with pytest.raises(ContractInvalidError):
        FixtureBundle.loads(raw, LIMITS)


def test_oversize_fixture_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "big.yaml"
    path.write_text("name: " + "x" * 200, encoding="utf-8")
    tight = Limits(max_file_bytes=64)
    with pytest.raises(LimitExceededError):
        load_fixture_file(path, tight)
