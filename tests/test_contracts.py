"""Contract loading tests: strict validation, format handling, D8 rule."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from resultseal.contracts import load_contract_data, load_contract_file
from resultseal.errors import ContractInvalidError, ParseFailedError
from resultseal.limits import Limits

REPO_ROOT = Path(__file__).resolve().parent.parent
LIMITS = Limits()


def minimal_contract() -> dict:
    return {
        "schema_version": "1",
        "claim_type": "not_found",
        "required_fields": [],
        "freshness": {"mode": "not_required"},
        "source_ref": "fixture://directory",
        "target_ref": "customer:42",
        "not_found_sentinel": "NOT_FOUND",
        "effect_evidence_required": False,
    }


def test_example_minimal_contract_loads() -> None:
    contract = load_contract_file(REPO_ROOT / "examples" / "minimal_contract.json", LIMITS)
    assert contract.claim_type.value == "not_found"
    assert contract.not_found_sentinel == "NOT_FOUND"


def test_unknown_key_rejected() -> None:
    raw = minimal_contract()
    raw["policy"] = "extra"
    with pytest.raises(ContractInvalidError):
        load_contract_data(raw, LIMITS)


def test_source_version_without_min_is_invalid() -> None:
    raw = minimal_contract()
    raw["freshness"] = {"mode": "source_version"}
    del raw["not_found_sentinel"]
    with pytest.raises(ContractInvalidError):
        load_contract_data(raw, LIMITS)


def test_source_version_with_min_is_valid() -> None:
    raw = minimal_contract()
    raw["freshness"] = {"mode": "source_version"}
    raw["min_source_version"] = "revision-17"
    del raw["not_found_sentinel"]
    assert load_contract_data(raw, LIMITS).min_source_version == "revision-17"


def test_max_age_requires_integer() -> None:
    raw = minimal_contract()
    raw["freshness"] = {"mode": "max_age_seconds"}
    with pytest.raises(ContractInvalidError):
        load_contract_data(raw, LIMITS)


@pytest.mark.parametrize(
    "mutation",
    [
        {"claim_type": "omniscient"},
        {"required_fields": ["ok", 1]},
        {"freshness": "fast"},
        {"schema_version": "2"},
        {"effect_evidence_required": "yes"},
    ],
)
def test_invalid_variants_rejected(mutation: dict) -> None:
    raw = minimal_contract()
    raw.update(mutation)
    with pytest.raises(ContractInvalidError):
        load_contract_data(raw, LIMITS)


def test_yaml_and_json_twins_load_identically(tmp_path) -> None:  # type: ignore[no-untyped-def]
    json_path = tmp_path / "c.json"
    yaml_path = tmp_path / "c.yaml"
    payload = minimal_contract()
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    yaml_path.write_text(
        "schema_version: '1'\n"
        "claim_type: not_found\n"
        "required_fields: []\n"
        "freshness:\n  mode: not_required\n"
        "source_ref: fixture://directory\n"
        "target_ref: customer:42\n"
        "not_found_sentinel: NOT_FOUND\n"
        "effect_evidence_required: false\n",
        encoding="utf-8",
    )
    assert load_contract_file(json_path, LIMITS) == load_contract_file(yaml_path, LIMITS)


def test_unsupported_suffix_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "c.txt"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ParseFailedError):
        load_contract_file(path, LIMITS)


def test_non_object_document_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "c.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ContractInvalidError):
        load_contract_file(path, LIMITS)
