"""Shipped raw-response examples must work through their adapters.

The JSON-schema side of example validation lives in test_schemas.py; this
module pins the runtime side: every raw-response example under examples/
must normalize cleanly and hash the content its adapter actually reads.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from resultseal.canonical import content_hash
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 10, 0, 1, tzinfo=UTC))


def test_http_empty_example_hashes_its_body() -> None:
    """The HTTP adapter hashes the body field; the example must carry one.

    http_empty.json demonstrates that an empty HTTP 200 cannot become
    not_found, so its content hash must cover the empty body it ships —
    not the null a missing field would produce.
    """
    raw = json.loads((EXAMPLES / "http_empty.json").read_text(encoding="utf-8"))
    normalization = normalize(raw, CLOCK)
    assert normalization.envelope.content_hash == content_hash("")


@pytest.mark.parametrize(
    "example", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.name
)
def test_example_normalizes_cleanly(example: Path) -> None:
    """Every raw-response example is a complete, normalizable input.

    Examples are copy-paste sources; one that fails normalization would
    teach a reader an incomplete input shape.
    """
    raw = json.loads((EXAMPLES / example.name).read_text(encoding="utf-8"))
    if "claim_type" in raw:
        pytest.skip("contract document, not a raw response")
    normalization = normalize(raw, CLOCK)
    assert normalization.envelope.transport_state is not None
