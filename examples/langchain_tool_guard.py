"""Guard a LangChain tool result before it enters model context."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from resultseal.contracts import load_contract_file
from resultseal.limits import Limits
from resultseal.models import Decision
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock, evaluate

CONTRACT_PATH = Path(__file__).with_name("customer_contract.json")


class BlockedObservation(RuntimeError):
    """Raised when ResultSeal blocks an unsafe tool observation."""


def guard_search_result(result: object) -> object:
    """Return a verified result or block the tool observation."""
    clock = ReferenceClock(now=datetime.now(UTC))
    contract = load_contract_file(CONTRACT_PATH, Limits())

    normalization = normalize(
        {
            "kind": "json",
            "source_ref": "mcp://crm-server",
            "target_ref": "customer:42",
            "tool_name": "search_customer",
            "body": result,
        },
        clock,
    )

    evaluation = evaluate(
        normalization.envelope,
        normalization.payload,
        contract,
        clock,
    )

    if evaluation.decision is not Decision.SEALED:
        codes = ", ".join(evaluation.reason_codes)
        raise BlockedObservation(
            f"ResultSeal blocked the tool observation: {codes}"
        )

    return normalization.payload


def build_tool():
    """Create a LangChain tool with a guarded result."""
    from langchain_core.tools import tool

    @tool
    def search_customer(query: str) -> object:
        """Search the customer database."""
        database_result: list[object] = []
        return guard_search_result(database_result)

    return search_customer


if __name__ == "__main__":
    build_tool()
