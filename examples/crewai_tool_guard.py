"""Guard a CrewAI tool result before it can propagate to sibling agents.

Install ``crewai`` to run the complete example. In a crew, one agent's tool
output is handed to others through shared task context, so an unverified
empty list blocked here cannot turn into a crew-wide hallucination. The
framework import stays inside :func:`build_tool`.
"""

from __future__ import annotations

from pathlib import Path

import resultseal
from resultseal import BlockedObservation

CONTRACT = resultseal.load_contract(Path(__file__).with_name("customer_contract.json"))


def guard_search_result(result: object) -> object:
    """Return *result* only if it seals as customer 42's complete record."""
    return resultseal.seal(
        {
            "kind": "json",
            "source_ref": "mcp://crm-server",
            "target_ref": "customer:42",
            "tool_name": "search_customer",
            "body": result,
        },
        CONTRACT,
    )


def build_tool():  # type annotations would require an optional dependency
    """Create a CrewAI tool whose output is sealed before agents share it."""
    from crewai.tools import tool

    @tool("Search Customer")
    def search_customer(query: str) -> object:
        """Search the customer database."""
        # Stand-in for a database call that matched nothing.
        database_result: list[object] = []
        return guard_search_result(database_result)

    return search_customer


if __name__ == "__main__":
    search_customer = build_tool()
    try:
        search_customer.run(query="customer 42")
    except BlockedObservation as exc:
        print(f"Blocked before reaching the crew: {exc}")
