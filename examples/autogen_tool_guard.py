"""Guard an AutoGen tool result before it enters the agent conversation.

Install ``autogen-agentchat`` and ``autogen-ext`` to run the complete
example. ``ReplayChatCompletionClient`` scripts the model's tool call, so the
run is deterministic and offline; swap in a real model client when adapting
the pattern. The framework imports stay inside :func:`build_agent` and the
``__main__`` block, so the guard itself runs without either dependency.

AutoGen catches exceptions raised by tools and records them in the chat as
an error result. Raising :class:`BlockedObservation` therefore puts the
refusal and its reason codes in front of every coordinating agent, where a
returned ``[]`` would have been read as "customer 42 does not exist".
"""

from __future__ import annotations

from pathlib import Path

import resultseal
from resultseal import BlockedObservation

__all__ = ["BlockedObservation", "build_agent", "guard_search_result", "search_customer"]

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


def search_customer(query: str) -> object:
    """Search the customer database."""
    # Stand-in for a database call that matched nothing.
    database_result: list[object] = []
    return guard_search_result(database_result)


def build_agent():  # type annotations would require optional dependencies
    """Create an offline AssistantAgent whose scripted model calls the guarded tool."""
    from autogen_agentchat.agents import AssistantAgent
    from autogen_core import FunctionCall
    from autogen_core.models import CreateResult, ModelFamily, ModelInfo, RequestUsage
    from autogen_ext.models.replay import ReplayChatCompletionClient

    scripted_call = CreateResult(
        finish_reason="function_calls",
        content=[
            FunctionCall(id="call_1", name="search_customer", arguments='{"query": "customer 42"}')
        ],
        usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
        cached=False,
    )
    model_info = ModelInfo(
        vision=False,
        function_calling=True,
        json_output=False,
        family=ModelFamily.UNKNOWN,
        structured_output=False,
    )
    return AssistantAgent(
        "crm_agent",
        model_client=ReplayChatCompletionClient([scripted_call], model_info=model_info),
        tools=[search_customer],
        system_message="Look up customers and report only verified observations.",
    )


if __name__ == "__main__":
    import asyncio

    from autogen_agentchat.messages import ToolCallExecutionEvent

    result = asyncio.run(build_agent().run(task="Find customer 42"))
    for message in result.messages:
        if isinstance(message, ToolCallExecutionEvent):
            for execution in message.content:
                print(f"is_error={execution.is_error}: {execution.content}")
