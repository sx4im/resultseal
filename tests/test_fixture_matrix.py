"""Fixture matrix through the library pipeline: every catalog outcome holds."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from resultseal.contracts import Contract
from resultseal.fixtures import load_fixture_file
from resultseal.limits import Limits
from resultseal.models import Decision
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock, evaluate

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "fixtures"
LIMITS = Limits()
CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))

NEGATIVE = [p for p in sorted(FIXTURES.glob("*.yaml")) if p.name != "unsafe-input.yaml"]


@pytest.mark.parametrize("path", NEGATIVE, ids=lambda p: p.name)
def test_catalog_expectation_holds(path: Path) -> None:
    bundle = load_fixture_file(path, LIMITS)
    contract: Contract | None = bundle.contract
    assert contract is not None, f"{path.name} must embed its contract"
    normalization = normalize(dict(bundle.raw_input), CLOCK)
    evaluation = evaluate(
        normalization.envelope, normalization.payload, contract, CLOCK
    )
    expected_decision = (
        Decision.SEALED
        if bundle.expected.decision_literal == "sealed"
        else Decision.BLOCKED
    )
    assert evaluation.decision is expected_decision, path.name
    if bundle.expected.truth_state is not None:
        assert evaluation.truth_state is bundle.expected.truth_state, path.name
    for code in bundle.expected.reason_codes:
        assert code in evaluation.reason_codes, path.name


def test_unsafe_input_is_refused_during_preparation() -> None:
    from resultseal.errors import UnsafeInputError
    from resultseal.normalize import prepare_payload

    bundle = load_fixture_file(FIXTURES / "unsafe-input.yaml", LIMITS)
    assert bundle.expected.decision_literal == "rejected"
    with pytest.raises(UnsafeInputError):
        prepare_payload(bundle.raw_input)
