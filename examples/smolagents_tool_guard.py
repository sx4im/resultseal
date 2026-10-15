"""Guard a smolagents tool result before it enters the agent's memory.

Install ``smolagents`` to run the complete example. When a guarded tool
raises inside an agent run, smolagents records the error as the step's
observation, so the model reads "observation blocked as empty" instead of an
empty list it would take as proof that the customer does not exist. The
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
    """Create a smolagents tool whose output is sealed before the agent sees it."""
    from smolagents import tool

    # smolagents derives the tool's input schema from these hints and the
    # Args section, so neither may be dropped.
    @tool
    def search_customer(query: str) -> dict:
        """Search the customer database.

        Args:
            query: Free-text description of the customer to look up.
        """
        # Stand-in for a database call that matched nothing.
        database_result: list[object] = []
        return guard_search_result(database_result)

    return search_customer


if __name__ == "__main__":
    search_customer = build_tool()
    try:
        search_customer(query="customer 42")
    except BlockedObservation as exc:
        print(f"Blocked before reaching the agent: {exc}")
