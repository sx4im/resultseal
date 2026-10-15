"""Guard a Pydantic-AI tool result before it can enter model context.

Install ``pydantic-ai`` to run the complete example. ``TestModel`` keeps the
example deterministic and offline; replace it with a production model when
adapting the pattern. The framework imports stay inside :func:`build_agent`.
"""

from __future__ import annotations

from pathlib import Path

import resultseal
from resultseal import BlockedObservation

CONTRACT = resultseal.load_contract(Path(__file__).with_name("customer_contract.json"))


def guard_customer_result(result: object) -> object:
    """Return *result* only if it seals as customer 42's complete record."""
    return resultseal.seal(
        {
            "kind": "json",
            "source_ref": "mcp://crm-server",
            "target_ref": "customer:42",
            "tool_name": "get_customer",
            "body": result,
        },
        CONTRACT,
    )


def build_agent():  # type annotations would require an optional dependency
    """Create an offline Pydantic-AI agent with a guarded tool."""
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    agent = Agent(
        TestModel(call_tools=["get_customer"]),
        instructions="Look up customer 42 and report only verified observations.",
    )

    @agent.tool_plain
    def get_customer(customer_id: str) -> object:
        """Look up a customer in the database."""
        # Stand-in for a database call that matched nothing. Raising here
        # keeps [] from becoming a successful ToolReturnPart.
        database_result: list[object] = []
        return guard_customer_result(database_result)

    return agent


if __name__ == "__main__":
    try:
        build_agent().run_sync("Find customer 42")
    except BlockedObservation as exc:
        print(f"Blocked before reaching the model: {exc}")
