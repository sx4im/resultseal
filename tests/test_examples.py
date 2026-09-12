"""Shipped raw-response examples must work through their adapters.

The JSON-schema side of example validation lives in test_schemas.py; this
module pins the runtime side: every raw-response example under examples/
must normalize cleanly and hash the content its adapter actually reads.
"""

from __future__ import annotations

import json
import runpy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from resultseal.canonical import content_hash
from resultseal.normalize import normalize
from resultseal.rules import ReferenceClock

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"

CLOCK = ReferenceClock(now=datetime(2026, 8, 21, 10, 0, 1, tzinfo=UTC))


def test_http_empty_example_hashes_its_body() -> None:
    """The HTTP adapter hashes the body field; the example must carry one.

    http_empty.json demonstrates that an empty HTTP 200 cannot become
    not_found, so its content hash must cover the empty body it ships —
    not the null a missing field would produce.
    """
    raw = json.loads((EXAMPLES / "http_empty.json").read_text(encoding="utf-8"))
    normalization = normalize(raw, CLOCK)
    assert normalization.envelope.content_hash == content_hash("")


@pytest.mark.parametrize(
    "example", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.name
)
def test_example_normalizes_cleanly(example: Path) -> None:
    """Every raw-response example is a complete, normalizable input.

    Examples are copy-paste sources; one that fails normalization would
    teach a reader an incomplete input shape.
    """
    raw = json.loads((EXAMPLES / example.name).read_text(encoding="utf-8"))
    if "claim_type" in raw:
        pytest.skip("contract document, not a raw response")
    normalization = normalize(raw, CLOCK)
    assert normalization.envelope.transport_state is not None


def test_pydantic_ai_example_blocks_empty_tool_result() -> None:
    """The framework-free guard is testable without optional Pydantic-AI."""
    namespace = runpy.run_path(EXAMPLES / "pydantic_ai_guard.py")
    with pytest.raises(
        namespace["BlockedObservation"], match="EMPTY_WITHOUT_NOT_FOUND_SENTINEL"
    ):
        namespace["guard_customer_result"]([])


def test_langchain_example_blocks_empty_tool_result() -> None:
    """The framework-free LangChain guard blocks empty results."""
    namespace = runpy.run_path(EXAMPLES / "langchain_tool_guard.py")
    with pytest.raises(
        namespace["BlockedObservation"],
        match="EMPTY_WITHOUT_NOT_FOUND_SENTINEL",
    ):
        namespace["guard_search_result"]([])


def test_langchain_example_docstring_documents_installation() -> None:
    """The example's module docstring instructs how to install optional dependencies."""
    doc = (EXAMPLES / "langchain_tool_guard.py").read_text(encoding="utf-8")
    assert "Install ``langchain-core``" in doc
    assert "search_customer.invoke" in doc or "build_tool().invoke" in doc


def test_llamaindex_example_blocks_empty_tool_result() -> None:
    """The framework-free LlamaIndex guard blocks empty results and seals verified ones."""
    namespace = runpy.run_path(EXAMPLES / "llamaindex_tool_guard.py")
    with pytest.raises(
        namespace["BlockedObservation"],
        match="EMPTY_WITHOUT_NOT_FOUND_SENTINEL",
    ):
        namespace["guard_search_result"]([])

    # Valid observation seals cleanly
    verified = namespace["guard_search_result"]({"customer_id": "42", "name": "Ada"})
    assert verified == {"customer_id": "42", "name": "Ada"}


def test_llamaindex_example_docstring_documents_installation() -> None:
    """The example documents how to install the optional LlamaIndex dependency."""
    doc = (EXAMPLES / "llamaindex_tool_guard.py").read_text(encoding="utf-8")
    assert "Install ``llama-index-core``" in doc
    assert "FunctionTool" in doc


def test_crewai_example_blocks_empty_tool_result() -> None:
    """The framework-free CrewAI guard blocks empty results and seals verified ones."""
    namespace = runpy.run_path(EXAMPLES / "crewai_tool_guard.py")
    with pytest.raises(
        namespace["BlockedObservation"],
        match="EMPTY_WITHOUT_NOT_FOUND_SENTINEL",
    ):
        namespace["guard_search_result"]([])

    # Valid observation seals cleanly
    verified = namespace["guard_search_result"]({"customer_id": "42", "name": "Ada"})
    assert verified == {"customer_id": "42", "name": "Ada"}


def test_crewai_example_docstring_documents_installation() -> None:
    """The example's module docstring instructs how to install optional dependencies."""
    doc = (EXAMPLES / "crewai_tool_guard.py").read_text(encoding="utf-8")
    assert "Install ``crewai``" in doc
    assert "search_customer.run" in doc or "build_tool().run" in doc


def test_langgraph_example_blocks_empty_tool_result() -> None:
    """The framework-free LangGraph guard blocks empty results and seals valid ones."""
    namespace = runpy.run_path(EXAMPLES / "langgraph_tool_guard.py")
    with pytest.raises(
        namespace["BlockedObservation"],
        match="EMPTY_WITHOUT_NOT_FOUND_SENTINEL",
    ):
        namespace["guard_search_result"]([])

    verified = namespace["guard_search_result"]({"customer_id": "42", "name": "Ada"})
    assert verified == {"customer_id": "42", "name": "Ada"}


def test_langgraph_example_docstring_documents_installation() -> None:
    """The example documents its optional LangGraph dependencies."""
    doc = (EXAMPLES / "langgraph_tool_guard.py").read_text(encoding="utf-8")
    assert "Install ``langgraph`` and ``langchain-core``" in doc
    assert "ToolNode" in doc
