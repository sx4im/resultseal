"""Schema conformance tests: shipped examples and fixture contracts validate."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import jsonschema
import pytest
import yaml

from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = REPO_ROOT / "schemas"
EXAMPLES = REPO_ROOT / "examples"
FIXTURES = REPO_ROOT / "fixtures"

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 10, 0, 1, tzinfo=UTC))

ENVELOPE_REQUIRED = frozenset(
    {
        "schema_version",
        "observation_id",
        "tool_call_id",
        "tool_name",
        "target_ref",
        "transport_state",
        "truth_state",
        "source_ref",
        "observed_at",
        "content_hash",
        "evidence_refs",
        "reason_codes",
    }
)


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_envelope_schema_required_fields_unchanged() -> None:
    schema = _load_schema("observation-envelope.v1.json")
    assert set(schema["required"]) == ENVELOPE_REQUIRED
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"] == {"const": "1"}


def test_contract_schema_has_min_source_version() -> None:
    schema = _load_schema("contract.v1.json")
    assert schema["properties"]["min_source_version"] == {
        "type": ["string", "null"],
        "maxLength": 256,
    }


@pytest.mark.parametrize(
    "example", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.name
)
def test_shipped_examples_validate(example: Path) -> None:
    raw = json.loads(example.read_text(encoding="utf-8"))
    if "claim_type" in raw:
        jsonschema.validate(raw, _load_schema("contract.v1.json"))
        return
    # Raw-response example: not itself a schema document, but it must
    # normalize into an envelope that satisfies the v1 envelope schema.
    normalization = normalize(raw, CLOCK)
    jsonschema.validate(
        normalization.envelope.to_dict(), _load_schema("observation-envelope.v1.json")
    )


@pytest.mark.parametrize(
    "fixture", sorted(FIXTURES.glob("*.yaml")), ids=lambda p: p.name
)
def test_embedded_fixture_contracts_validate(fixture: Path) -> None:
    doc = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    if isinstance(doc, dict) and isinstance(doc.get("contract"), dict):
        jsonschema.validate(doc["contract"], _load_schema("contract.v1.json"))
