"""Guard a LangGraph tool result before it enters graph state.

Install ``langgraph`` and ``langchain-core`` to run the complete example.
The framework imports stay inside :func:`build_node` and the ``__main__``
block, so the guard itself runs without either dependency.
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


def build_node():  # type annotations would require optional dependencies
    """Create a LangGraph ToolNode with a guarded customer-search tool."""
    from langchain_core.tools import tool
    from langgraph.prebuilt import ToolNode

    @tool
    def search_customer(query: str) -> object:
        """Search the customer database."""
        # Stand-in for a database call that matched nothing. An empty result
        # must not enter graph state as if it were a verified observation.
        database_result: list[object] = []
        return guard_search_result(database_result)

    # Pass handle_tool_errors=True to hand the block to the model as an error
    # ToolMessage instead of raising out of the graph.
    return ToolNode([search_customer])


if __name__ == "__main__":
    from langchain_core.messages import AIMessage
    from langgraph.graph import END, START, MessagesState, StateGraph

    builder = StateGraph(MessagesState)
    builder.add_node("tools", build_node())
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    graph = builder.compile()

    ai_call = AIMessage(
        content="",
        tool_calls=[{"name": "search_customer", "args": {"query": "customer 42"}, "id": "call_1"}],
    )
    try:
        graph.invoke({"messages": [ai_call]})
    except BlockedObservation as exc:
        print(f"Blocked before entering graph state: {exc}")
