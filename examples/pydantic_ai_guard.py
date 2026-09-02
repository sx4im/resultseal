"""Guard a Pydantic-AI tool result before it can enter model context.

Install ``pydantic-ai`` to run the complete example.  ``TestModel`` keeps the
example deterministic and offline; replace it with a production model when
adapting the pattern.
"""

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
    """Raised before an unverified tool result is returned to the agent."""


def guard_customer_result(result: object) -> object:
    """Return a verified observation, or abort the tool call with evidence."""
    clock = ReferenceClock(now=datetime.now(UTC))
    contract = load_contract_file(CONTRACT_PATH, Limits())
    normalization = normalize(
        {
            "kind": "json",
            "source_ref": "mcp://crm-server",
            "target_ref": "customer:42",
            "tool_name": "get_customer",
            "body": result,
        },
        clock,
    )
    evaluation = evaluate(normalization.envelope, normalization.payload, contract, clock)
    if evaluation.decision is not Decision.SEALED:
        codes = ", ".join(evaluation.reason_codes)
        raise BlockedObservation(f"ResultSeal blocked the tool observation: {codes}")
    return normalization.payload


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
        """Look up a customer in a database."""
        # Stand-in for a database call. Raising here prevents [] from becoming
        # a successful ToolReturnPart in the next model request.
        database_result: list[object] = []
        return guard_customer_result(database_result)

    return agent


if __name__ == "__main__":
    build_agent().run_sync("Find customer 42")
