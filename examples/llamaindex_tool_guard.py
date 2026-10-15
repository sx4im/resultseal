"""Guard a LlamaIndex tool result before it enters model context.

Install ``llama-index-core`` to run the complete example. The framework
import stays inside :func:`build_tool`, so the guard itself runs without it.
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
    """Create a LlamaIndex FunctionTool whose output is sealed first."""
    from llama_index.core.tools import FunctionTool

    def search_customer(query: str) -> object:
        """Search the customer database."""
        # Stand-in for a retrieval call that matched nothing. An empty result
        # must not enter agent context as if it were a verified answer.
        database_result: list[object] = []
        return guard_search_result(database_result)

    return FunctionTool.from_defaults(fn=search_customer)


if __name__ == "__main__":
    search_customer = build_tool()
    try:
        search_customer.call(query="customer 42")
    except BlockedObservation as exc:
        print(f"Blocked before reaching the model: {exc}")
