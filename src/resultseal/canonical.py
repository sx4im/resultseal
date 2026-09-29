"""Canonical JSON serialization and deterministic hashes.

Canonical form: UTF-8, recursively sorted object keys, ``,``/``:`` separators,
no insignificant whitespace, non-ASCII preserved, integers untouched, NaN/Inf
and non-string object keys rejected. ``datetime.date`` / ``datetime.datetime`` /
``datetime.time`` values (which YAML's ``timestamp`` tag may produce) render as
ISO-8601 strings, so explicitly allowed YAML input always canonicalizes.
``deterministic_fingerprint`` is defined over a decision record that excludes
the fingerprint field itself (decision D6).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime, time

from resultseal.errors import SchemaInvalidError
from resultseal.models import JsonValue

FINGERPRINT_KEY = "deterministic_fingerprint"


def canonical_json(obj: JsonValue) -> bytes:
    """Serialize to canonical bytes or raise SchemaInvalidError."""
    _validate(obj)
    normalized = _normalize(obj)
    try:
        text = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SchemaInvalidError(
            "value is not canonically serializable", detail=str(exc)
        ) from exc
    return text.encode("utf-8")


def content_hash(obj: JsonValue) -> str:
    """``sha256:<hex>`` over the canonical serialization of *obj*."""
    digest = hashlib.sha256(canonical_json(obj)).hexdigest()
    return f"sha256:{digest}"


def decision_fingerprint(record: Mapping[str, JsonValue]) -> str:
    """``sha256:<hex>`` over the record minus its own fingerprint field."""
    trimmed = {k: v for k, v in record.items() if k != FINGERPRINT_KEY}
    return content_hash(trimmed)


def _normalize(obj: object) -> JsonValue:
    # datetime is a subclass of date: check it first.
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, float):
        return 0.0 if obj == 0.0 else obj
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(item) for item in obj]
    return obj  # type: ignore[return-value]


def _validate(obj: JsonValue) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise SchemaInvalidError(
                    "object keys must be strings", detail=repr(key)[:80]
                )
            _validate(value)
    elif isinstance(obj, list):
        for item in obj:
            _validate(item)
