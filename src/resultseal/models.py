"""Typed, immutable core models.

Envelopes and contracts are frozen dataclasses with strict construction:
unknown keys, missing fields, wrong types, out-of-bounds sizes, and unknown
enum values are rejected, never coerced. Models perform no I/O and make no
policy decisions.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from resultseal.errors import ContractInvalidError, SchemaInvalidError

SCHEMA_VERSION = "1"

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

_EnumT = TypeVar("_EnumT", bound=StrEnum)

_CONTENT_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REASON_CODE_RE = re.compile(r"^[A-Z0-9_]+$")


class TransportState(StrEnum):
    """How far the request travelled, regardless of meaning."""

    ATTEMPTED = "attempted"
    DISPATCHED = "dispatched"
    TRANSPORTED = "transported"
    TRANSPORT_ERROR = "transport_error"


class TruthState(StrEnum):
    """Semantic classification of what was observed."""

    OBSERVED = "observed"
    COMPLETE = "complete"
    EMPTY = "empty"
    NOT_FOUND = "not_found"
    PARTIAL = "partial"
    STALE = "stale"
    SOURCE_MISMATCH = "source_mismatch"
    UNVERIFIED_EFFECT = "unverified_effect"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"
    SEALED = "sealed"


class ClaimType(StrEnum):
    """MVP claim classes a contract may declare."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    READ_COMPLETE = "read_complete"
    EFFECT_OBSERVED = "effect_observed"
    TASK_COMPLETE = "task_complete"


class Decision(StrEnum):
    """Final promotion decision."""

    SEALED = "sealed"
    BLOCKED = "blocked"


class FreshnessMode(StrEnum):
    NOT_REQUIRED = "not_required"
    SOURCE_VERSION = "source_version"
    MAX_AGE_SECONDS = "max_age_seconds"


def _check_str(value: object, name: str, *, max_len: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise SchemaInvalidError(f"field {name!r} must be a string")
    if not value and not allow_empty:
        raise SchemaInvalidError(f"field {name!r} must be non-empty")
    if len(value) > max_len:
        raise SchemaInvalidError(f"field {name!r} exceeds {max_len} characters")
    return value


def _check_str_list(
    value: object, name: str, *, max_items: int, max_len: int
) -> tuple[str, ...]:
    if not isinstance(value, tuple) or any(not isinstance(v, str) for v in value):
        raise SchemaInvalidError(f"field {name!r} must be a tuple of strings")
    if len(value) > max_items:
        raise SchemaInvalidError(f"field {name!r} exceeds {max_items} items")
    for item in value:
        _check_str(item, f"{name}[]", max_len=max_len)
    return value


@dataclass(frozen=True)
class ObservationEnvelope:
    """Versioned observation separating transport facts from semantic truth."""

    observation_id: str
    tool_call_id: str
    tool_name: str
    target_ref: str
    transport_state: TransportState
    truth_state: TruthState
    source_ref: str
    observed_at: str
    content_hash: str
    evidence_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    source_version: str | None = None
    metadata: Mapping[str, JsonScalar] = field(
        default_factory=lambda: MappingProxyType({})
    )
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise SchemaInvalidError(
                "unsupported envelope schema_version", detail=repr(self.schema_version)
            )
        _check_str(self.observation_id, "observation_id", max_len=256)
        _check_str(self.tool_call_id, "tool_call_id", max_len=256)
        _check_str(self.tool_name, "tool_name", max_len=256)
        _check_str(self.target_ref, "target_ref", max_len=1024)
        _check_str(self.source_ref, "source_ref", max_len=1024)
        _check_str(self.observed_at, "observed_at", max_len=64)
        if not isinstance(self.content_hash, str) or not _CONTENT_HASH_RE.fullmatch(
            self.content_hash
        ):
            raise SchemaInvalidError(
                "content_hash must match sha256:<64 lowercase hex>"
            )
        _check_str_list(self.evidence_refs, "evidence_refs", max_items=64, max_len=2048)
        _check_str_list(self.reason_codes, "reason_codes", max_items=64, max_len=64)
        for code in self.reason_codes:
            if not _REASON_CODE_RE.fullmatch(code):
                raise SchemaInvalidError(
                    "reason codes must be uppercase [A-Z0-9_]", detail=code
                )
        if not isinstance(self.transport_state, TransportState):
            raise SchemaInvalidError("transport_state must be a TransportState")
        if not isinstance(self.truth_state, TruthState):
            raise SchemaInvalidError("truth_state must be a TruthState")
        if self.source_version is not None:
            _check_str(self.source_version, "source_version", max_len=256)
        _check_metadata(self.metadata)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "target_ref": self.target_ref,
            "transport_state": self.transport_state.value,
            "truth_state": self.truth_state.value,
            "source_ref": self.source_ref,
            "observed_at": self.observed_at,
            "content_hash": self.content_hash,
            "evidence_refs": list(self.evidence_refs),
            "reason_codes": list(self.reason_codes),
            "source_version": self.source_version,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> ObservationEnvelope:
        allowed = {f.name for f in fields(cls)}
        unknown = set(raw) - allowed
        if unknown:
            raise SchemaInvalidError(
                "unknown envelope fields", detail=", ".join(sorted(unknown))
            )
        missing = allowed - set(raw)
        if missing:
            raise SchemaInvalidError(
                "missing envelope fields", detail=", ".join(sorted(missing))
            )
        return cls(
            observation_id=_as_str(raw, "observation_id"),
            tool_call_id=_as_str(raw, "tool_call_id"),
            tool_name=_as_str(raw, "tool_name"),
            target_ref=_as_str(raw, "target_ref"),
            transport_state=_as_enum(raw, "transport_state", TransportState),
            truth_state=_as_enum(raw, "truth_state", TruthState),
            source_ref=_as_str(raw, "source_ref"),
            observed_at=_as_str(raw, "observed_at"),
            content_hash=_as_str(raw, "content_hash"),
            evidence_refs=_as_str_list(raw, "evidence_refs"),
            reason_codes=_as_str_list(raw, "reason_codes"),
            source_version=_as_opt_str(raw, "source_version"),
            metadata=_as_metadata(raw),
            schema_version=_as_str(raw, "schema_version"),
        )


def _check_metadata(metadata: Mapping[str, JsonScalar]) -> None:
    if not isinstance(metadata, Mapping):
        raise SchemaInvalidError("metadata must be an object")
    if len(metadata) > 64:
        raise SchemaInvalidError("metadata exceeds 64 properties")
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise SchemaInvalidError("metadata keys must be strings")
        if isinstance(value, dict | list):
            raise SchemaInvalidError(
                "metadata values must be scalars", detail=f"key {key!r}"
            )


def _as_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if value is None:
        raise SchemaInvalidError(f"missing required field {key!r}")
    if not isinstance(value, str):
        raise SchemaInvalidError(f"field {key!r} must be a string")
    return value


def _as_opt_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SchemaInvalidError(f"field {key!r} must be a string or null")
    return value


def _as_str_list(raw: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise SchemaInvalidError(f"field {key!r} must be an array of strings")
    return tuple(value)


def _as_enum(raw: Mapping[str, object], key: str, enum_cls: type[_EnumT]) -> _EnumT:
    value = raw.get(key)
    if value is None:
        raise SchemaInvalidError(f"missing required field {key!r}")
    if not isinstance(value, str):
        raise SchemaInvalidError(
            f"field {key!r} must be a string", detail=repr(value)
        )
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise SchemaInvalidError(
            f"field {key!r} is not a valid {enum_cls.__name__}", detail=repr(value)
        ) from exc


def _as_metadata(raw: Mapping[str, object]) -> Mapping[str, JsonScalar]:
    value = raw.get("metadata")
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, dict):
        raise SchemaInvalidError("metadata must be an object")
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class Contract:
    """Declarative promotion requirements for one claim class."""

    claim_type: ClaimType
    required_fields: tuple[str, ...]
    freshness_mode: FreshnessMode
    max_age_seconds: int | None
    min_source_version: str | None
    source_ref: str
    target_ref: str
    not_found_sentinel: str | None = None
    effect_evidence_required: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractInvalidError(
                "unsupported contract schema_version", detail=repr(self.schema_version)
            )
        if not isinstance(self.claim_type, ClaimType):
            raise ContractInvalidError("claim_type must be a ClaimType")
        if not isinstance(self.freshness_mode, FreshnessMode):
            raise ContractInvalidError("freshness_mode must be a FreshnessMode")
        if not isinstance(self.required_fields, tuple) or any(
            not isinstance(f, str) for f in self.required_fields
        ):
            raise ContractInvalidError("required_fields must be a tuple of strings")
        if len(self.required_fields) > 64:
            raise ContractInvalidError("required_fields exceeds 64 items")
        for name in self.required_fields:
            if not name or len(name) > 256:
                raise ContractInvalidError(
                    "required_fields entries must be 1..256 characters"
                )
        if self.max_age_seconds is not None:
            if isinstance(self.max_age_seconds, bool) or not isinstance(
                self.max_age_seconds, int
            ):
                raise ContractInvalidError("max_age_seconds must be an integer")
            if not 0 <= self.max_age_seconds <= 31_536_000:
                raise ContractInvalidError("max_age_seconds must be 0..31536000")
        if self.min_source_version is not None:
            _check_str_contract(self.min_source_version, "min_source_version", 256)
        _check_str_contract(self.source_ref, "source_ref", 1024)
        _check_str_contract(self.target_ref, "target_ref", 1024)
        if self.not_found_sentinel is not None:
            _check_str_contract(self.not_found_sentinel, "not_found_sentinel", 256)
        if not isinstance(self.effect_evidence_required, bool):
            raise ContractInvalidError("effect_evidence_required must be boolean")
        if self.freshness_mode is FreshnessMode.MAX_AGE_SECONDS:
            if self.max_age_seconds is None:
                raise ContractInvalidError(
                    "max_age_seconds is required when mode is max_age_seconds"
                )
        elif self.max_age_seconds is not None:
            raise ContractInvalidError(
                "max_age_seconds is only valid when mode is max_age_seconds"
            )
        if self.freshness_mode is FreshnessMode.SOURCE_VERSION and not (
            self.min_source_version
        ):
            raise ContractInvalidError(
                "min_source_version is required when mode is source_version"
            )

    def to_dict(self) -> dict[str, JsonValue]:
        freshness: dict[str, JsonValue] = {"mode": self.freshness_mode.value}
        if self.freshness_mode is FreshnessMode.MAX_AGE_SECONDS:
            freshness["max_age_seconds"] = self.max_age_seconds
        return {
            "schema_version": self.schema_version,
            "claim_type": self.claim_type.value,
            "required_fields": list(self.required_fields),
            "freshness": freshness,
            "min_source_version": self.min_source_version,
            "source_ref": self.source_ref,
            "target_ref": self.target_ref,
            "not_found_sentinel": self.not_found_sentinel,
            "effect_evidence_required": self.effect_evidence_required,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> Contract:
        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ContractInvalidError(
                "unsupported contract schema_version", detail=repr(version)
            )
        allowed = {
            "schema_version",
            "claim_type",
            "required_fields",
            "freshness",
            "min_source_version",
            "source_ref",
            "target_ref",
            "not_found_sentinel",
            "effect_evidence_required",
        }
        unknown = set(raw) - allowed
        if unknown:
            raise ContractInvalidError(
                "unknown contract fields", detail=", ".join(sorted(unknown))
            )
        missing = {"schema_version", "claim_type", "required_fields", "freshness",
                   "source_ref", "target_ref"} - set(raw)
        if missing:
            raise ContractInvalidError(
                "missing contract fields", detail=", ".join(sorted(missing))
            )
        freshness_raw = raw.get("freshness")
        if not isinstance(freshness_raw, dict):
            raise ContractInvalidError("freshness must be an object")
        unknown_freshness = set(freshness_raw) - {"mode", "max_age_seconds"}
        if unknown_freshness:
            raise ContractInvalidError(
                "unknown freshness fields",
                detail=", ".join(sorted(unknown_freshness)),
            )
        mode_raw = freshness_raw.get("mode")
        if not isinstance(mode_raw, str):
            raise ContractInvalidError(
                "freshness.mode must be a string", detail=repr(mode_raw)
            )
        try:
            mode = FreshnessMode(mode_raw)
        except ValueError as exc:
            raise ContractInvalidError(
                "freshness.mode is not valid", detail=repr(mode_raw)
            ) from exc
        max_age_raw = freshness_raw.get("max_age_seconds")
        if max_age_raw is not None and (
            isinstance(max_age_raw, bool) or not isinstance(max_age_raw, int)
        ):
            raise ContractInvalidError("max_age_seconds must be an integer or null")
        effect_flag = raw.get("effect_evidence_required", False)
        if not isinstance(effect_flag, bool):
            raise ContractInvalidError("effect_evidence_required must be boolean")
        claim_raw = raw.get("claim_type")
        if not isinstance(claim_raw, str):
            raise ContractInvalidError(
                "claim_type must be a string", detail=repr(claim_raw)
            )
        try:
            claim = ClaimType(claim_raw)
        except ValueError as exc:
            raise ContractInvalidError(
                "claim_type is not a declared claim class", detail=repr(claim_raw)
            ) from exc
        fields_raw = raw.get("required_fields")
        if not isinstance(fields_raw, list) or any(
            not isinstance(f, str) for f in fields_raw
        ):
            raise ContractInvalidError("required_fields must be an array of strings")
        return cls(
            claim_type=claim,
            required_fields=tuple(fields_raw),
            freshness_mode=mode,
            max_age_seconds=max_age_raw,
            min_source_version=_as_opt_str(raw, "min_source_version"),
            source_ref=_as_str(raw, "source_ref"),
            target_ref=_as_str(raw, "target_ref"),
            not_found_sentinel=_as_opt_str(raw, "not_found_sentinel"),
            effect_evidence_required=effect_flag,
        )


def _check_str_contract(value: object, name: str, max_len: int) -> str:
    if not isinstance(value, str):
        raise ContractInvalidError(f"field {name!r} must be a string")
    if not value:
        raise ContractInvalidError(f"field {name!r} must be non-empty")
    if len(value) > max_len:
        raise ContractInvalidError(f"field {name!r} exceeds {max_len} characters")
    return value
