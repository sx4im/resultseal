"""Guard a LangChain tool result before it enters model context.

Install ``langchain-core`` to run the complete example. The framework import
stays inside :func:`build_tool`, so the guard itself runs without it.
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
    """Create a LangChain tool whose output is sealed before the model sees it."""
    from langchain_core.tools import tool

    @tool
    def search_customer(query: str) -> object:
        """Search the customer database."""
        # Stand-in for a database call that matched nothing. Without the
        # guard, the model would read [] as "customer 42 does not exist".
        database_result: list[object] = []
        return guard_search_result(database_result)

    return search_customer


if __name__ == "__main__":
    search_customer = build_tool()
    try:
        search_customer.invoke({"query": "customer 42"})
    except BlockedObservation as exc:
        print(f"Blocked before reaching the model: {exc}")
