"""Bounded-input limits, enforced before and immediately after parsing."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from resultseal.errors import LimitExceededError, SchemaInvalidError
from resultseal.models import JsonValue


@dataclass(frozen=True)
class Limits:
    """Resource ceilings for untrusted documents."""

    max_file_bytes: int = 131_072
    max_depth: int = 32
    max_nodes: int = 4_096
    max_string_chars: int = 16_384


def check_size(num_bytes: int, limits: Limits) -> None:
    if num_bytes > limits.max_file_bytes:
        raise LimitExceededError(
            f"input exceeds {limits.max_file_bytes} bytes",
            detail=f"got {num_bytes} bytes",
        )


def walk_bounds(obj: JsonValue, limits: Limits) -> None:
    """Enforce depth, node-count, and string-length bounds on parsed data."""
    budget = _Budget(limits)
    _walk(obj, 1, budget)


class _Budget:
    __slots__ = ("limits", "nodes")

    def __init__(self, limits: Limits) -> None:
        self.limits = limits
        self.nodes = 0


def _walk(obj: JsonValue, depth: int, budget: _Budget) -> None:
    if depth > budget.limits.max_depth:
        raise LimitExceededError(f"nesting exceeds {budget.limits.max_depth} levels")
    budget.nodes += 1
    if budget.nodes > budget.limits.max_nodes:
        raise LimitExceededError(
            f"document exceeds {budget.limits.max_nodes} nodes"
        )
    if isinstance(obj, float) and not isfinite(obj):
        raise SchemaInvalidError("numbers must be finite")
    if isinstance(obj, str):
        _check_string(obj, budget.limits)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str):
                budget.nodes += 1
                _check_string(key, budget.limits)
            _walk(value, depth + 1, budget)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, depth + 1, budget)


def _check_string(value: str, limits: Limits) -> None:
    if len(value) > limits.max_string_chars:
        raise LimitExceededError(f"strings exceed {limits.max_string_chars} characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise SchemaInvalidError("strings must be valid UTF-8") from exc
