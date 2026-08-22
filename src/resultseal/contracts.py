"""Contract loading: declarative data only, strictly validated."""

from __future__ import annotations

from pathlib import Path

from resultseal.errors import ContractInvalidError, ParseFailedError
from resultseal.limits import Limits
from resultseal.models import Contract
from resultseal.safeio import load_json, load_yaml

_JSON_SUFFIXES = {".json"}
_YAML_SUFFIXES = {".yaml", ".yml"}


def load_contract_file(path: Path, limits: Limits) -> Contract:
    """Load and validate a contract from ``.json`` or ``.yaml``."""
    suffix = path.suffix.lower()
    if suffix in _JSON_SUFFIXES:
        doc = _read(path, limits, loader=load_json)
    elif suffix in _YAML_SUFFIXES:
        doc = _read(path, limits, loader=load_yaml)
    else:
        raise ParseFailedError(
            "unsupported contract format", detail=f"extension {suffix!r}"
        )
    return load_contract_data(doc, limits)


def load_contract_data(doc: object, limits: Limits) -> Contract:
    if not isinstance(doc, dict):
        raise ContractInvalidError("contract must be an object")
    return Contract.from_dict(doc)


def _read(path: Path, limits: Limits, loader) -> object:  # type: ignore[no-untyped-def]
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ParseFailedError(
            "contract file could not be read", detail=str(exc)[:120]
        ) from exc
    return loader(data, limits)
