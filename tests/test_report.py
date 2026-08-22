"""Report tests: exact record shape, fingerprints, rendering, redaction."""

from __future__ import annotations

import json

from resultseal.models import (
    ClaimType,
    Contract,
    Decision,
    FreshnessMode,
    ObservationEnvelope,
    TransportState,
    TruthState,
)
from resultseal.report import (
    build_record,
    redact_record,
    render_json,
    render_markdown,
    with_fingerprint,
)
from resultseal.rules import Evaluation

VERSION = "0.1.0"

ENVELOPE = ObservationEnvelope(
    observation_id="obs-demo",
    tool_call_id="call-demo",
    tool_name="lookup_customer",
    target_ref="customer:42",
    transport_state=TransportState.TRANSPORTED,
    truth_state=TruthState.OBSERVED,
    source_ref="fixture://directory",
    observed_at="2026-08-21T10:00:00Z",
    content_hash="sha256:" + "1" * 64,
)

CONTRACT = Contract(
    claim_type=ClaimType.READ_COMPLETE,
    required_fields=("customer_id", "name", "email"),
    freshness_mode=FreshnessMode.SOURCE_VERSION,
    max_age_seconds=None,
    min_source_version="revision-17",
    source_ref="fixture://directory",
    target_ref="customer:42",
)

EVALUATION = Evaluation(
    decision=Decision.BLOCKED,
    truth_state=TruthState.PARTIAL,
    reason_codes=("MISSING_REQUIRED_FIELD",),
)


def test_record_has_exactly_the_specified_fields() -> None:
    record = build_record(EVALUATION, ENVELOPE, CONTRACT, resultseal_version=VERSION)
    assert set(record) == {
        "resultseal_version",
        "decision",
        "truth_state",
        "claim_type",
        "reason_codes",
        "observation_id",
        "tool_call_id",
        "source_ref",
        "evidence_refs",
    }


def test_fingerprint_added_last_and_stable() -> None:
    record = build_record(EVALUATION, ENVELOPE, CONTRACT, resultseal_version=VERSION)
    stamped = with_fingerprint(record)
    assert stamped["deterministic_fingerprint"].startswith("sha256:")
    assert with_fingerprint(record) == stamped


def test_render_json_is_byte_stable_and_parses() -> None:
    record = with_fingerprint(
        build_record(EVALUATION, ENVELOPE, CONTRACT, resultseal_version=VERSION)
    )
    first = render_json(record)
    second = render_json(record)
    assert first == second
    assert json.loads(first)["decision"] == "blocked"


def test_render_markdown_sections() -> None:
    record = with_fingerprint(
        build_record(EVALUATION, ENVELOPE, CONTRACT, resultseal_version=VERSION)
    )
    text = render_markdown(
        record,
        input_summary="HTTP 200 from fixture://directory targeting customer:42",
        normalized_state=(
            f"transport={ENVELOPE.transport_state.value} "
            f"observed={ENVELOPE.truth_state.value}"
        ),
        clock_note="2026-08-21T12:00:00Z",
    )
    for heading in ("Input", "Normalized state", "Claim", "Decision", "Reason codes", "Evidence"):
        assert f"## {heading}" in text
    assert "MISSING_REQUIRED_FIELD" in text


def test_redaction_replaces_named_fields() -> None:
    record = build_record(EVALUATION, ENVELOPE, CONTRACT, resultseal_version=VERSION)
    redacted = redact_record(record, ("source_ref",))
    assert redacted["source_ref"] == "[REDACTED]"
    assert record["source_ref"] == "fixture://directory"  # original untouched


def test_no_payload_in_record() -> None:
    record = build_record(EVALUATION, ENVELOPE, CONTRACT, resultseal_version=VERSION)
    encoded = json.dumps(record)
    assert "Ada" not in encoded
    assert "customer_id" not in encoded
