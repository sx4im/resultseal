"""High-level API: one call from a raw tool result to a promotion decision.

``check`` runs the same pipeline as ``resultseal check`` — input bounds,
adapter, pure rules — and returns a :class:`CheckResult`. ``seal`` is the
guard form: it returns the verified payload or raises
:class:`BlockedObservation`, so a blocked observation cannot reach an agent
through a forgotten ``if``.

Like the CLI, this module is an entrypoint: when ``now`` is omitted it reads
the wall clock once to build the injected reference clock. The rules engine
itself never does (D10).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from resultseal._version import __version__
from resultseal.contracts import load_contract_data, load_contract_file
from resultseal.errors import SchemaInvalidError
from resultseal.limits import Limits, walk_bounds
from resultseal.models import Contract, Decision, JsonValue, ObservationEnvelope, TruthState
from resultseal.normalize import normalize
from resultseal.report import build_record, with_fingerprint
from resultseal.rules import Evaluation, ReferenceClock, evaluate


@dataclass(frozen=True)
class CheckResult:
    """The outcome of evaluating one tool result against one contract."""

    decision: Decision
    truth_state: TruthState
    reason_codes: tuple[str, ...]
    envelope: ObservationEnvelope
    payload: object
    contract: Contract

    @property
    def sealed(self) -> bool:
        return self.decision is Decision.SEALED

    def record(self) -> dict[str, JsonValue]:
        """The fingerprinted decision record ``resultseal check --format json`` prints."""
        evaluation = Evaluation(self.decision, self.truth_state, self.reason_codes)
        record = build_record(
            evaluation, self.envelope, self.contract, resultseal_version=__version__
        )
        return with_fingerprint(record)


class BlockedObservation(Exception):
    """Raised by :func:`seal` when a tool result may not support its claim.

    Deliberately not a :class:`~resultseal.errors.ResultSealError`: those mean
    the input was invalid or unsafe, whereas a blocked observation is a valid
    input that was evaluated and refused.
    """

    def __init__(self, result: CheckResult) -> None:
        self.result = result
        codes = ", ".join(result.reason_codes)
        super().__init__(f"observation blocked as {result.truth_state.value}: {codes}")

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return self.result.reason_codes


def load_contract(
    source: str | Path | Mapping[str, object], *, limits: Limits | None = None
) -> Contract:
    """Load a contract from a ``.json`` / ``.yaml`` path or an already-parsed mapping."""
    bounds = limits if limits is not None else Limits()
    if isinstance(source, Mapping):
        return load_contract_data(dict(source), bounds)
    return load_contract_file(Path(source), bounds)


def check(
    raw: Mapping[str, object],
    contract: Contract,
    *,
    now: datetime | None = None,
    limits: Limits | None = None,
) -> CheckResult:
    """Normalize *raw* with its adapter and evaluate it against *contract*.

    *raw* is an adapter input — the same object a ``resultseal check``
    response file holds, e.g. ``{"kind": "json", "source_ref": ...,
    "target_ref": ..., "body": <tool output>}``. *now* must be
    timezone-aware; pin it for replay-stable ``max_age_seconds`` verdicts.

    Raises :class:`~resultseal.errors.ResultSealError` for invalid or
    unsafe input. A blocked observation is a normal return value.
    """
    if not isinstance(raw, Mapping):
        raise SchemaInvalidError("tool result must be an object")
    # Adapters treat every value as JSON-shaped; walk_bounds enforces the same
    # limits the CLI applies to files, and canonical hashing rejects any
    # value that is not JSON-serializable.
    document = cast("dict[str, JsonValue]", dict(raw))
    walk_bounds(document, limits if limits is not None else Limits())
    clock = ReferenceClock(now=datetime.now(UTC) if now is None else now)
    normalization = normalize(document, clock)
    evaluation = evaluate(normalization.envelope, normalization.payload, contract, clock)
    return CheckResult(
        decision=evaluation.decision,
        truth_state=evaluation.truth_state,
        reason_codes=evaluation.reason_codes,
        envelope=normalization.envelope,
        payload=normalization.payload,
        contract=contract,
    )


def seal(
    raw: Mapping[str, object],
    contract: Contract,
    *,
    now: datetime | None = None,
    limits: Limits | None = None,
) -> object:
    """Return the verified payload, or raise :class:`BlockedObservation`."""
    result = check(raw, contract, now=now, limits=limits)
    if not result.sealed:
        raise BlockedObservation(result)
    return result.payload
