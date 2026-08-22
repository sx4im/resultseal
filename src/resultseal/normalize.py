"""Adapters translating raw tool-result shapes into observation envelopes.

Adapters establish structural facts only. HTTP 2xx establishes ``transported``
— never completeness, not-found, or a seal. Zero exit codes establish process
completion only. An empty structured object is never not-found. Adapters are
deterministic, bounded, side-effect-free: they accept values, never URLs to
fetch, and never execute returned strings.

Envelope identity defaults (D11): caller-provided ids win; otherwise
``obs-<12hex>`` / ``call-<12hex>`` are derived from the payload content hash.
``observed_at`` falls back to the injected clock. ``kind`` selects the
adapter explicitly, or is inferred: mcp (structuredContent/isError/
outputSchema) -> stdio (exit_code/stdout/stderr) -> http_json (status_code)
-> json.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from resultseal.canonical import content_hash
from resultseal.errors import SchemaInvalidError
from resultseal.limits import Limits
from resultseal.models import JsonScalar, JsonValue, ObservationEnvelope, TransportState, TruthState
from resultseal.rules import ReferenceClock
from resultseal.safeio import load_yaml

_KINDS = frozenset({"http_json", "json", "yaml", "mcp", "stdio", "claim_only"})

_MCP_KEYS = ("structuredContent", "isError", "outputSchema")
_STDIO_KEYS = ("exit_code", "stdout", "stderr")


@dataclass(frozen=True)
class Normalization:
    envelope: ObservationEnvelope
    payload: object


def infer_kind(raw: Mapping[str, JsonValue]) -> str:
    explicit = raw.get("kind")
    if explicit is not None:
        if explicit not in _KINDS:
            raise SchemaInvalidError(
                "unknown input kind", detail=repr(explicit)
            )
        return str(explicit)
    if any(key in raw for key in _MCP_KEYS):
        return "mcp"
    if any(key in raw for key in _STDIO_KEYS):
        return "stdio"
    if "status_code" in raw:
        return "http_json"
    return "json"


def prepare_payload(raw: Mapping[str, JsonValue], limits: Limits | None = None) -> object:
    """Parse the nested YAML document text of a ``kind: yaml`` input."""
    value = raw.get("value")
    if not isinstance(value, str):
        raise SchemaInvalidError("yaml inputs require a string 'value'")
    return load_yaml(value.encode("utf-8"), limits or Limits())


def normalize(
    raw: Mapping[str, JsonValue],
    clock: ReferenceClock,
) -> Normalization:
    kind = infer_kind(raw)
    handler = {
        "http_json": _normalize_http,
        "json": _normalize_json,
        "yaml": _normalize_yaml,
        "mcp": _normalize_mcp,
        "stdio": _normalize_stdio,
        "claim_only": _normalize_claim_only,
    }[kind]
    return handler(kind, raw, clock)


def _normalize_http(
    kind: str, raw: Mapping[str, JsonValue], clock: ReferenceClock
) -> Normalization:
    status = raw.get("status_code")
    if isinstance(status, bool) or not isinstance(status, int):
        raise SchemaInvalidError("status_code must be an integer")
    # ADAPTERS.md: HTTP inputs may name the target via any of these fields;
    # the response's own target is the most specific evidence.
    effective_target = raw
    if "target_ref" not in raw and "response_target" in raw:
        effective_target = {**raw, "target_ref": raw["response_target"]}
    elif "target_ref" not in raw and "request_target" in raw:
        effective_target = {**raw, "target_ref": raw["request_target"]}
    raw = effective_target
    body = raw.get("body")
    if 200 <= status < 400:
        transport = TransportState.TRANSPORTED
        payload, parse_failed = _parse_body(body)
        truth = TruthState.PARSE_ERROR if parse_failed else TruthState.OBSERVED
    else:
        transport = TransportState.TRANSPORT_ERROR
        payload, truth = None, TruthState.UNKNOWN
    hashed = body
    envelope = _envelope(
        raw,
        clock,
        transport_state=transport,
        truth_state=truth,
        content_source=hashed,
        payload=payload,
    )
    return Normalization(envelope, payload)


def _normalize_json(
    kind: str, raw: Mapping[str, JsonValue], clock: ReferenceClock
) -> Normalization:
    body = raw.get("body")
    payload, parse_failed = _parse_body(body)
    truth = TruthState.PARSE_ERROR if parse_failed else TruthState.OBSERVED
    envelope = _envelope(
        raw,
        clock,
        transport_state=TransportState.TRANSPORTED,
        truth_state=truth,
        content_source=body,
        payload=payload,
    )
    return Normalization(envelope, payload)


def _normalize_yaml(
    kind: str, raw: Mapping[str, JsonValue], clock: ReferenceClock
) -> Normalization:
    # prepare_payload runs the nested document through safeio: unsafe tags
    # raise UnsafeInputError here, before any evaluation happens.
    payload = prepare_payload(raw)
    envelope = _envelope(
        raw,
        clock,
        transport_state=TransportState.TRANSPORTED,
        truth_state=TruthState.OBSERVED,
        content_source=raw.get("value"),
        payload=payload,
    )
    return Normalization(envelope, payload)


def _normalize_mcp(
    kind: str, raw: Mapping[str, JsonValue], clock: ReferenceClock
) -> Normalization:
    structured = raw.get("structuredContent")
    text = raw.get("text")
    is_error = raw.get("isError") is True
    if structured is not None:
        payload: object = structured
    elif isinstance(text, str):
        payload = text
    else:
        payload = None
    metadata_extra: dict[str, JsonScalar] = {}
    if is_error:
        metadata_extra["protocol_conflict"] = True
    schema = raw.get("outputSchema")
    missing = _missing_schema_fields(schema, structured)
    if missing:
        metadata_extra["missing_schema_fields"] = ",".join(missing)
    envelope = _envelope(
        raw,
        clock,
        transport_state=TransportState.TRANSPORTED,
        truth_state=TruthState.OBSERVED,
        content_source=structured if structured is not None else text,
        payload=payload,
        metadata_extra=metadata_extra,
    )
    return Normalization(envelope, payload)


def _normalize_stdio(
    kind: str, raw: Mapping[str, JsonValue], clock: ReferenceClock
) -> Normalization:
    exit_code = raw.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        raise SchemaInvalidError("exit_code must be an integer")
    stdout = raw.get("stdout")
    command = raw.get("command")
    metadata_extra: dict[str, JsonScalar] = {}
    if isinstance(command, str):
        metadata_extra["command"] = command
    if exit_code != 0:
        envelope = _envelope(
            raw,
            clock,
            transport_state=TransportState.TRANSPORT_ERROR,
            truth_state=TruthState.UNKNOWN,
            content_source=stdout,
            payload=None,
            metadata_extra=metadata_extra,
        )
        return Normalization(envelope, None)
    output_format = raw.get("output_format")
    if output_format == "json" and isinstance(stdout, str):
        payload, parse_failed = _parse_body(stdout)
        truth = TruthState.PARSE_ERROR if parse_failed else TruthState.OBSERVED
    else:
        payload = stdout if isinstance(stdout, str) and stdout else (
            stdout if isinstance(stdout, (dict, list)) else None
        )
        truth = TruthState.OBSERVED
    envelope = _envelope(
        raw,
        clock,
        transport_state=TransportState.TRANSPORTED,
        truth_state=truth,
        content_source=stdout,
        payload=payload,
        metadata_extra=metadata_extra,
    )
    return Normalization(envelope, payload)


def _normalize_claim_only(
    kind: str, raw: Mapping[str, JsonValue], clock: ReferenceClock
) -> Normalization:
    claim = raw.get("claim")
    metadata_extra: dict[str, JsonScalar] = {}
    if isinstance(claim, str):
        metadata_extra["claimed_text"] = claim[:200]
    envelope = _envelope(
        raw,
        clock,
        transport_state=TransportState.ATTEMPTED,
        truth_state=TruthState.UNKNOWN,
        content_source=claim,
        payload=None,
        metadata_extra=metadata_extra,
        default_source_ref="local://claim",
        default_target_ref="unknown-target",
    )
    return Normalization(envelope, None)


def _missing_schema_fields(schema: object, payload: object) -> list[str]:
    if not isinstance(schema, dict):
        return []
    required = schema.get("required")
    if not isinstance(required, list) or not isinstance(payload, dict):
        return []
    return [name for name in required if isinstance(name, str) and name not in payload]


def _parse_body(body: object) -> tuple[object, bool]:
    """Return (payload, parse_failed). Structured bodies pass through."""
    if body is None or body == "":
        return None, False
    if isinstance(body, str):
        try:
            return json.loads(body), False
        except json.JSONDecodeError:
            return None, True
    if isinstance(body, (dict, list, int, float, bool)):
        return body, False
    return None, True


def _envelope(
    raw: Mapping[str, JsonValue],
    clock: ReferenceClock,
    *,
    transport_state: TransportState,
    truth_state: TruthState,
    content_source: object,
    payload: object,
    metadata_extra: dict[str, JsonScalar] | None = None,
    default_source_ref: str | None = None,
    default_target_ref: str | None = None,
) -> ObservationEnvelope:
    source_ref = raw.get("source_ref")
    if source_ref is None:
        source_ref = default_source_ref
    if not isinstance(source_ref, str) or not source_ref:
        raise SchemaInvalidError("source_ref must be a non-empty string")
    target_ref = raw.get("target_ref")
    if target_ref is None:
        target_ref = default_target_ref
    if not isinstance(target_ref, str) or not target_ref:
        raise SchemaInvalidError("target_ref must be a non-empty string")
    tool_name = raw.get("tool_name")
    if tool_name is None:
        tool_name = "unspecified-tool"
    if not isinstance(tool_name, str):
        raise SchemaInvalidError("tool_name must be a string")

    # Adapter inputs arrive from JSON/YAML documents, so the hashed content
    # is JSON-shaped by construction; canonical_json rejects anything else.
    digest = content_hash(content_source)  # type: ignore[arg-type]
    short = digest.split(":", 1)[1][:12]

    observation_id = raw.get("observation_id")
    tool_call_id = raw.get("tool_call_id")
    observed_at = raw.get("observed_at")
    evidence_raw = raw.get("evidence_refs")
    evidence_refs: tuple[str, ...] = ()
    if evidence_raw is not None:
        if not isinstance(evidence_raw, list) or any(
            not isinstance(e, str) for e in evidence_raw
        ):
            raise SchemaInvalidError("evidence_refs must be an array of strings")
        # Validated above; narrow past JsonValue for tuple().
        evidence_refs = tuple(cast("list[str]", evidence_raw))
    source_version = raw.get("source_version")
    if source_version is not None and not isinstance(source_version, str):
        raise SchemaInvalidError("source_version must be a string or null")

    metadata: dict[str, JsonScalar] = {"input_kind": infer_kind(raw)}
    user_metadata = raw.get("metadata")
    if isinstance(user_metadata, dict):
        for key, value in user_metadata.items():
            if not isinstance(key, str) or isinstance(value, (dict, list)):
                continue  # silently bounded: non-scalars never enter envelopes
            metadata[key] = value
    if metadata_extra:
        metadata.update(metadata_extra)

    return ObservationEnvelope(
        observation_id=(
            observation_id if isinstance(observation_id, str) else f"obs-{short}"
        ),
        tool_call_id=(
            tool_call_id if isinstance(tool_call_id, str) else f"call-{short}"
        ),
        tool_name=tool_name,
        target_ref=target_ref,
        transport_state=transport_state,
        truth_state=truth_state,
        source_ref=source_ref,
        observed_at=(
            observed_at
            if isinstance(observed_at, str)
            else _format_clock(clock.now)
        ),
        content_hash=digest,
        evidence_refs=evidence_refs,
        reason_codes=(),
        source_version=source_version,
        metadata=metadata,
    )


def _format_clock(now: datetime) -> str:
    utc = now.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
