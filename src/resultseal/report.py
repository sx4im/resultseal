"""Decision records and deterministic reports.

The decision record contains exactly the R8.1 fields; it never carries raw
payloads, headers, or wall-clock timestamps. JSON rendering is canonical
(sorted keys, no whitespace variance), so replays are byte-identical.
Markdown rendering targets a developer terminal.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from resultseal.canonical import canonical_json, decision_fingerprint
from resultseal.models import Contract, JsonValue, ObservationEnvelope
from resultseal.rules import Evaluation

_FINGERPRINT_KEY = "deterministic_fingerprint"


def build_record(
    evaluation: Evaluation,
    envelope: ObservationEnvelope,
    contract: Contract,
    *,
    resultseal_version: str,
) -> dict[str, JsonValue]:
    """Assemble the normalized decision record (no fingerprint yet)."""
    return {
        "resultseal_version": resultseal_version,
        "decision": evaluation.decision.value,
        "truth_state": evaluation.truth_state.value,
        "claim_type": contract.claim_type.value,
        "reason_codes": list(evaluation.reason_codes),
        "observation_id": envelope.observation_id,
        "tool_call_id": envelope.tool_call_id,
        "source_ref": envelope.source_ref,
        "evidence_refs": list(envelope.evidence_refs),
    }


def with_fingerprint(record: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Return a copy of *record* with its deterministic fingerprint added."""
    stamped = dict(record)
    stamped[_FINGERPRINT_KEY] = decision_fingerprint(record)
    return stamped


def redact_record(
    record: Mapping[str, JsonValue], fields: Sequence[str]
) -> dict[str, JsonValue]:
    """Replace named top-level fields with ``[REDACTED]`` (original untouched)."""
    redacted = dict(record)
    for name in fields:
        if name in redacted:
            redacted[name] = "[REDACTED]"
    return redacted


def render_json(record: Mapping[str, JsonValue]) -> str:
    """Canonical JSON text: stable across processes and replays."""
    return canonical_json(dict(record)).decode("utf-8")


def render_markdown(
    record: Mapping[str, JsonValue],
    *,
    input_summary: str,
    normalized_state: str,
    clock_note: str | None = None,
) -> str:
    """Terminal-readable report with the six CLI_CONTRACT sections."""
    codes_raw = record.get("reason_codes") or []
    codes = [str(code) for code in codes_raw] if isinstance(codes_raw, list) else []
    codes_text = ", ".join(codes) if codes else "(none)"
    evidence_raw = record.get("evidence_refs")
    if isinstance(evidence_raw, list) and evidence_raw:
        evidence_text = "\n".join(f"- {ref}" for ref in evidence_raw)
    else:
        evidence_text = "(none)"
    lines = [
        "# ResultSeal Report",
        "",
        "## Input",
        input_summary,
        "",
        "## Normalized state",
        normalized_state,
        "",
        "## Claim",
        f"claim_type: {record.get('claim_type')}",
        "",
        "## Decision",
        f"{record.get('decision')} (truth_state: {record.get('truth_state')})",
        "",
        "## Reason codes",
        codes_text,
        "",
        "## Evidence",
        evidence_text,
        "",
        f"fingerprint: {record.get(_FINGERPRINT_KEY)}",
    ]
    if clock_note:
        lines.insert(len(lines) - 1, f"reference clock: {clock_note}")
    return "\n".join(lines) + "\n"
