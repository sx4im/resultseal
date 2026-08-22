"""Integration: a naive promotion path trusts observations ResultSeal blocks.

This is the executable statement of the product promise (MASTER_BUILD_PROMPT
Phase 7): ``naive_promote`` embodies the common anti-pattern — transport
status and payload presence collapse into one binary success — while
ResultSeal's contract-gated pipeline refuses each case.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from resultseal.fixtures import load_fixture_file
from resultseal.limits import Limits
from resultseal.models import Decision
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock, evaluate

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "fixtures"
LIMITS = Limits()
CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))


def naive_transport_promote(status_code: int) -> bool:
    """Anti-pattern 1: any 2xx counts as verified success."""
    return 200 <= status_code < 300


def naive_content_promote(status_code: int, body: object) -> bool:
    """Anti-pattern 2: 2xx plus non-empty content counts as verified."""
    return naive_transport_promote(status_code) and body not in (None, "")


def _verdict(fixture_name: str) -> Decision:
    bundle = load_fixture_file(FIXTURES / fixture_name, LIMITS)
    assert bundle.contract is not None
    normalization = normalize(dict(bundle.raw_input), CLOCK)
    evaluation = evaluate(
        normalization.envelope, normalization.payload, bundle.contract, CLOCK
    )
    return evaluation.decision


def test_empty_http_200_is_not_not_found() -> None:
    assert naive_transport_promote(200) is True
    assert _verdict("empty-result.yaml") is Decision.BLOCKED


def test_partial_response_does_not_become_found() -> None:
    assert naive_content_promote(200, {"customer_id": "42"}) is True
    assert _verdict("partial-response.yaml") is Decision.BLOCKED


def test_stale_revision_does_not_become_fresh() -> None:
    assert naive_content_promote(200, {"customer_id": "42", "name": "Ada"}) is True
    assert _verdict("stale-response.yaml") is Decision.BLOCKED


def test_wrong_target_does_not_become_a_match() -> None:
    assert naive_content_promote(200, {"customer_id": "42", "name": "Ada"}) is True
    assert _verdict("wrong-target.yaml") is Decision.BLOCKED


def test_claimed_write_without_evidence_stays_unverified() -> None:
    assert naive_content_promote(200, {"status": "updated"}) is True
    assert _verdict("unverified-write.yaml") is Decision.BLOCKED


def test_missing_dispatch_cannot_become_success() -> None:
    # A model's claim alone is metadata, never evidence: there was no call.
    assert _verdict("no-dispatch-success-claim.yaml") is Decision.BLOCKED


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("explicit-not-found.yaml", Decision.SEALED),
        ("complete-fresh-result.yaml", Decision.SEALED),
        ("malformed-json.yaml", Decision.BLOCKED),
    ],
)
def test_positive_and_malformed_paths(fixture: str, expected: Decision) -> None:
    assert _verdict(fixture) is expected
