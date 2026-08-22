"""Determinism: repeated replay produces identical records and fingerprints."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from resultseal.fixtures import load_fixture_file
from resultseal.limits import Limits
from resultseal.normalize import normalize
from resultseal.report import build_record, render_json, with_fingerprint
from resultseal.rules import ReferenceClock, evaluate

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "fixtures"
LIMITS = Limits()
CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))


def _record_for(path: Path) -> str:
    bundle = load_fixture_file(path, LIMITS)
    assert bundle.contract is not None
    normalization = normalize(dict(bundle.raw_input), CLOCK)
    evaluation = evaluate(
        normalization.envelope, normalization.payload, bundle.contract, CLOCK
    )
    record = build_record(
        evaluation,
        normalization.envelope,
        bundle.contract,
        resultseal_version="0.1.0",
    )
    return render_json(with_fingerprint(record))


def test_every_fixture_replays_byte_identically() -> None:
    for path in sorted(FIXTURES.glob("*.yaml")):
        if path.name == "unsafe-input.yaml":
            continue  # refused before any record exists
        first = _record_for(path)
        second = _record_for(path)
        assert first == second != "", path.name


def test_fingerprints_differ_across_fixtures() -> None:
    seen: dict[str, Path] = {}
    for path in sorted(FIXTURES.glob("*.yaml")):
        if path.name == "unsafe-input.yaml":
            continue
        record = _record_for(path)
        assert record not in seen, f"{path.name} collides with {seen[record].name}"
        seen[record] = path
