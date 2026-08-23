"""ResultSeal: deterministic observation-integrity contracts for AI-agent tool results.

ResultSeal classifies tool observations and decides, via an explicit declarative
contract, whether a raw tool response may support a downstream factual claim.
Unknown and incomplete evidence is blocked by default: HTTP 200 is not an
observation, empty is not not-found, and a tool call is not an effect.
"""

from __future__ import annotations

__version__ = "0.1.1"

__all__ = ["__version__"]
