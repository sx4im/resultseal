"""ResultSeal: deterministic observation-integrity contracts for AI-agent tool results.

ResultSeal classifies tool observations and decides, via an explicit declarative
contract, whether a raw tool response may support a downstream factual claim.
Unknown and incomplete evidence is blocked by default: HTTP 200 is not an
observation, empty is not not-found, and a tool call is not an effect.

Typical use guards a tool before its output reaches the model::

    contract = resultseal.load_contract("customer_contract.json")
    payload = resultseal.seal(
        {"kind": "json", "source_ref": "mcp://crm-server",
         "target_ref": "customer:42", "body": tool_output},
        contract,
    )  # raises resultseal.BlockedObservation unless sealed
"""

from __future__ import annotations

from resultseal._version import __version__
from resultseal.api import BlockedObservation, CheckResult, check, load_contract, seal
from resultseal.errors import ResultSealError
from resultseal.models import ClaimType, Contract, Decision, TruthState

__all__ = [
    "BlockedObservation",
    "CheckResult",
    "ClaimType",
    "Contract",
    "Decision",
    "ResultSealError",
    "TruthState",
    "__version__",
    "check",
    "load_contract",
    "seal",
]
