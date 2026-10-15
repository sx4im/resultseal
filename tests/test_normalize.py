"""Shared normalizer behavior: kind inference, ID policy, nested YAML, purity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from resultseal.errors import SchemaInvalidError, UnsafeInputError
from resultseal.models import ClaimType, JsonValue, TransportState, TruthState
from resultseal.normalize import infer_kind, normalize, prepare_payload
from resultseal.rules import ReferenceClock

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC))


def test_infer_kind_explicit_wins() -> None:
    assert infer_kind({"kind": "stdio", "status_code": 200}) == "stdio"


def test_infer_kind_unknown_explicit_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        infer_kind({"kind": "carrier_pigeon"})


@pytest.mark.parametrize("kind", [["json"], {"a": 1}, 7, True])
def test_infer_kind_non_string_explicit_rejected(kind: object) -> None:
    with pytest.raises(SchemaInvalidError):
        infer_kind({"kind": kind})  # type: ignore[dict-item]


def test_infer_kind_structured() -> None:
    assert infer_kind({"structuredContent": {}}) == "mcp"
    assert infer_kind({"isError": False}) == "mcp"


def test_infer_kind_stdio() -> None:
    assert infer_kind({"exit_code": 0, "stdout": "ok"}) == "stdio"


def test_infer_kind_http() -> None:
    assert infer_kind({"status_code": 200}) == "http_json"


def test_infer_kind_defaults_to_json() -> None:
    assert infer_kind({"body": {"a": 1}}) == "json"


def test_derived_ids_are_deterministic_and_stable() -> None:
    raw = {"kind": "json", "source_ref": "s", "target_ref": "t", "body": {"a": 1}}
    first = normalize(raw, CLOCK)
    second = normalize(raw, CLOCK)
    assert first.envelope.observation_id == second.envelope.observation_id
    assert first.envelope.observation_id.startswith("obs-")
    assert len(first.envelope.observation_id) == len("obs-") + 12
    assert first.envelope.tool_call_id.startswith("call-")
    assert first.envelope.observed_at == "2026-08-21T12:00:00Z"


def test_provided_ids_and_timestamp_win() -> None:
    raw = {
        "kind": "json",
        "source_ref": "s",
        "target_ref": "t",
        "body": {"a": 1},
        "observation_id": "obs-mine",
        "tool_call_id": "call-mine",
        "observed_at": "2026-01-01T00:00:00Z",
    }
    env = normalize(raw, CLOCK).envelope
    assert env.observation_id == "obs-mine"
    assert env.tool_call_id == "call-mine"
    assert env.observed_at == "2026-01-01T00:00:00Z"


def _yaml_input(observed_at_line: bytes) -> dict[str, JsonValue]:
    from resultseal.limits import Limits
    from resultseal.safeio import load_yaml

    raw = load_yaml(
        b"kind: json\nsource_ref: s\ntarget_ref: t\nbody: {a: 1}\n" + observed_at_line,
        Limits(),
    )
    assert isinstance(raw, dict)
    return raw


def test_unquoted_yaml_observed_at_is_kept_not_replaced_by_clock() -> None:
    raw = _yaml_input(b"observed_at: 2020-01-01T00:00:00Z\n")
    env = normalize(raw, CLOCK).envelope
    assert env.observed_at == "2020-01-01T00:00:00+00:00"


def test_unquoted_yaml_observed_at_still_fails_max_age_freshness() -> None:
    from resultseal.models import Contract, Decision, FreshnessMode
    from resultseal.rules import evaluate

    contract = Contract(
        claim_type=ClaimType.FOUND,
        required_fields=("a",),
        freshness_mode=FreshnessMode.MAX_AGE_SECONDS,
        max_age_seconds=60,
        min_source_version=None,
        source_ref="s",
        target_ref="t",
    )
    norm = normalize(_yaml_input(b"observed_at: 2020-01-01T00:00:00Z\n"), CLOCK)
    evaluation = evaluate(norm.envelope, norm.payload, contract, CLOCK)
    assert evaluation.decision is Decision.BLOCKED
    assert evaluation.reason_codes == ("STALE_OBSERVATION",)


def test_non_string_observed_at_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        normalize(
            {"kind": "json", "source_ref": "s", "target_ref": "t", "body": {}, "observed_at": 0},
            CLOCK,
        )


def test_nested_yaml_payload_loads() -> None:
    raw = {
        "kind": "yaml",
        "source_ref": "s",
        "target_ref": "t",
        "value": "customer_id: \"42\"\nname: Ada\n",
    }
    result = normalize(raw, CLOCK)
    assert result.payload == {"customer_id": "42", "name": "Ada"}
    assert result.envelope.transport_state is TransportState.TRANSPORTED


def test_nested_yaml_custom_tag_rejected_before_evaluation() -> None:
    raw = {
        "kind": "yaml",
        "source_ref": "s",
        "target_ref": "t",
        "value": "!!python/object/apply:os.system ['echo unsafe']",
    }
    with pytest.raises(UnsafeInputError):
        prepare_payload(raw)


def test_json_body_string_parses_or_marks_parse_error() -> None:
    ok = normalize(
        {"kind": "json", "source_ref": "s", "target_ref": "t", "body": "{\"a\": 1}"},
        CLOCK,
    )
    assert ok.payload == {"a": 1}
    bad = normalize(
        {"kind": "json", "source_ref": "s", "target_ref": "t", "body": "{broken"},
        CLOCK,
    )
    assert bad.envelope.truth_state is TruthState.PARSE_ERROR
    assert bad.payload is None


def test_missing_source_or_target_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        normalize({"kind": "json", "target_ref": "t", "body": {}}, CLOCK)
    with pytest.raises(SchemaInvalidError):
        normalize({"kind": "json", "source_ref": "s", "body": {}}, CLOCK)


def test_evidence_refs_validated() -> None:
    with pytest.raises(SchemaInvalidError):
        normalize(
            {
                "kind": "json",
                "source_ref": "s",
                "target_ref": "t",
                "body": {"a": 1},
                "evidence_refs": [42],
            },
            CLOCK,
        )


def test_same_input_twice_is_identical_envelope() -> None:
    raw = {
        "kind": "http_json",
        "status_code": 200,
        "source_ref": "fixture://directory",
        "target_ref": "customer:42",
        "body": "",
    }
    first = normalize(raw, CLOCK)
    second = normalize(raw, CLOCK)
    assert first.envelope == second.envelope
    assert first.envelope.content_hash == second.envelope.content_hash


def test_claim_only_is_attempted() -> None:
    result = normalize({"kind": "claim_only", "claim": "done"}, CLOCK)
    assert result.envelope.transport_state is TransportState.ATTEMPTED
    assert result.payload is None


def test_yaml_timestamp_in_payload_normalizes() -> None:
    # YAML's timestamp tag is explicitly allowed by safeio, so a date inside
    # the payload must canonicalize (ISO-8601) rather than explode hashing.
    from resultseal.limits import Limits
    from resultseal.safeio import load_yaml

    raw = load_yaml(
        b"kind: mcp\nsource_ref: s\ntarget_ref: t\n"
        b"structuredContent:\n  observed_on: 2026-01-01\n  name: x\n",
        Limits(),
    )
    assert isinstance(raw, dict)
    first = normalize(raw, CLOCK)
    second = normalize(raw, CLOCK)
    assert first.envelope.content_hash == second.envelope.content_hash
    assert first.envelope.content_hash.startswith("sha256:")
