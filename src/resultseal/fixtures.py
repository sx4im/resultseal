"""Fixture-bundle loading for the offline negative-test runner.

A fixture is one bounded YAML (or JSON) document::

    fixture_version: 1
    name: <id>
    claim_type: <optional ClaimType hint>
    contract: <optional inline v1 contract; required for replay>
    input:    <adapter-shaped raw response>
    expected:
      decision: sealed | blocked | rejected
      truth_state: <optional expected final truth state>
      reason_codes: [<subset that must be present>]

``decision: rejected`` asserts the loader itself must refuse the document
(unsafe input) before any evaluation. There is no implicit contract lookup
(D9): a bundle without ``contract`` loads but cannot be replayed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from resultseal.contracts import load_contract_data
from resultseal.errors import ContractInvalidError, ParseFailedError
from resultseal.limits import Limits
from resultseal.models import ClaimType, Contract, Decision, JsonValue, TruthState
from resultseal.rules import Evaluation
from resultseal.safeio import load_json, load_yaml

_ALLOWED_KEYS = frozenset(
    {"fixture_version", "name", "claim_type", "contract", "input", "expected"}
)
_REQUIRED_KEYS = frozenset({"fixture_version", "name", "input", "expected"})
_DECISIONS = frozenset({"sealed", "blocked", "rejected"})


@dataclass(frozen=True)
class Expectation:
    decision_literal: str
    truth_state: TruthState | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class FixtureBundle:
    name: str
    raw_input: Mapping[str, JsonValue]
    expected: Expectation
    claim_hint: ClaimType | None = None
    contract: Contract | None = None

    def requires_contract(self) -> bool:
        return self.expected.decision_literal != "rejected"

    @classmethod
    def loads(cls, text: str, limits: Limits) -> FixtureBundle:
        return _build(load_yaml(text.encode("utf-8"), limits), limits)

    @classmethod
    def from_json_bytes(cls, data: bytes, limits: Limits) -> FixtureBundle:
        return _build(load_json(data, limits), limits)


def expectation_matches(expected: Expectation, evaluation: Evaluation) -> bool:
    """True when *evaluation* satisfies the bundle's declared expectation.

    ``decision_literal`` maps onto the two-value ``Decision`` vocabulary
    (``rejected`` bundles never reach evaluation); ``truth_state`` and
    ``reason_codes`` are checked only when declared, codes as a subset.
    """
    expected_decision = (
        Decision.SEALED if expected.decision_literal == "sealed" else Decision.BLOCKED
    )
    if evaluation.decision is not expected_decision:
        return False
    if (
        expected.truth_state is not None
        and evaluation.truth_state is not expected.truth_state
    ):
        return False
    return all(code in evaluation.reason_codes for code in expected.reason_codes)


def load_fixture_file(path: Path, limits: Limits) -> FixtureBundle:
    suffix = path.suffix.lower()
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ParseFailedError(
            "fixture file could not be read", detail=str(exc)[:120]
        ) from exc
    if suffix == ".json":
        doc = load_json(data, limits)
    elif suffix in (".yaml", ".yml"):
        doc = load_yaml(data, limits)
    else:
        raise ParseFailedError(
            "unsupported fixture format", detail=f"extension {suffix!r}"
        )
    return _build(doc, limits)


def _build(doc: object, limits: Limits) -> FixtureBundle:
    if not isinstance(doc, dict):
        raise ContractInvalidError("fixture must be an object")
    unknown = set(doc) - _ALLOWED_KEYS
    if unknown:
        raise ContractInvalidError(
            "unknown fixture fields", detail=", ".join(sorted(str(k) for k in unknown))
        )
    missing = _REQUIRED_KEYS - set(doc)
    if missing:
        raise ContractInvalidError(
            "missing fixture fields", detail=", ".join(sorted(missing))
        )
    version = doc.get("fixture_version")
    if version != 1:
        raise ContractInvalidError(
            "unsupported fixture_version", detail=repr(version)
        )
    name = doc.get("name")
    if not isinstance(name, str) or not name or len(name) > 256:
        raise ContractInvalidError("fixture name must be a non-empty string")

    claim_hint = _claim_hint(doc.get("claim_type"))
    contract = _embedded_contract(doc.get("contract"), limits)
    raw_input = doc.get("input")
    if not isinstance(raw_input, dict):
        raise ContractInvalidError("input must be an object")
    expected = _expectation(doc.get("expected"))
    return FixtureBundle(
        name=name,
        raw_input=raw_input,
        expected=expected,
        claim_hint=claim_hint,
        contract=contract,
    )


def _claim_hint(value: object) -> ClaimType | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractInvalidError(
            "fixture claim_type must be a string", detail=repr(value)
        )
    try:
        return ClaimType(value)
    except ValueError as exc:
        raise ContractInvalidError(
            "fixture claim_type is not a declared claim class", detail=repr(value)
        ) from exc


def _embedded_contract(value: object, limits: Limits) -> Contract | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ContractInvalidError("embedded contract must be an object")
    return load_contract_data(value, limits)


def _expectation(value: object) -> Expectation:
    if not isinstance(value, dict):
        raise ContractInvalidError("expected must be an object")
    unknown = set(value) - {"decision", "truth_state", "reason_codes"}
    if unknown:
        raise ContractInvalidError(
            "unknown expected fields",
            detail=", ".join(sorted(str(k) for k in unknown)),
        )
    decision = value.get("decision")
    if decision not in _DECISIONS:
        raise ContractInvalidError(
            "expected.decision must be sealed | blocked | rejected",
            detail=repr(decision),
        )
    truth_raw = value.get("truth_state")
    truth: TruthState | None = None
    if truth_raw is not None:
        try:
            truth = TruthState(truth_raw)
        except (TypeError, ValueError) as exc:
            raise ContractInvalidError(
                "expected.truth_state is not a valid truth state",
                detail=repr(truth_raw),
            ) from exc
    codes_raw = value.get("reason_codes")
    if codes_raw is None:
        codes_raw = []
    if not isinstance(codes_raw, list) or any(not isinstance(c, str) for c in codes_raw):
        raise ContractInvalidError("expected.reason_codes must be an array of strings")
    return Expectation(
        decision_literal=str(decision),
        truth_state=truth,
        reason_codes=tuple(codes_raw),
    )
