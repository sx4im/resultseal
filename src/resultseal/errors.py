"""Stable error taxonomy.

Every failure carries a stable uppercase ``code`` (public API per
ERROR_CODES.md) and the CLI exit code it maps to. Exception text is
diagnostic detail only; the code is the contract.
"""

from __future__ import annotations

from typing import ClassVar


class ResultSealError(Exception):
    """Base class for every ResultSeal failure."""

    code: ClassVar[str] = "RESULTSEAL_ERROR"
    exit_code: ClassVar[int] = 2

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:
        text = f"{self.code}: {self.message}"
        if self.detail:
            text = f"{text} ({self.detail})"
        return text


class InvalidInputError(ResultSealError):
    """Structurally invalid input; never evaluated. CLI exit 2."""

    code = "SCHEMA_INVALID"
    exit_code = 2


class SchemaInvalidError(InvalidInputError):
    """A document does not match its declared structure."""


class ParseFailedError(InvalidInputError):
    """A payload could not be parsed under the applicable format."""

    code = "PARSE_FAILED"


class ContractInvalidError(InvalidInputError):
    """A contract is malformed or requests unsupported semantics."""

    code = "CONTRACT_INVALID"


class UnsupportedClaimError(InvalidInputError):
    """The requested claim class is not declared by any provided contract."""

    code = "UNSUPPORTED_CLAIM"


class InvalidArgumentError(InvalidInputError):
    """The invocation itself is malformed (bad flag value, wrong arity)."""

    code = "INVALID_ARGUMENT"


class UnsafeInputError(ResultSealError):
    """Input rejected for safety before evaluation. CLI exit 3."""

    code = "UNSAFE_INPUT"
    exit_code = 3


class LimitExceededError(UnsafeInputError):
    """A bounded-input limit was exceeded before or during parse."""

    code = "LIMIT_EXCEEDED"


class PathEscapeError(UnsafeInputError):
    """A path resolves outside its allowed root."""
