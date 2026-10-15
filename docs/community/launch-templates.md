# Community Launch & Listing Templates

This document provides ready-to-use launch templates, submission blurbs, and ecosystem PR entries to promote ResultSeal across developer communities.

---

## 1. Hacker News (Show HN)

**Title:**
> Show HN: ResultSeal – Fail-closed observation contracts for AI-agent tool results

**URL / Text:**
> https://github.com/sx4im/resultseal

**First Comment / Intro:**
> Hi HN,
>
> Tool-calling agents keep turning non-answers into facts:
> - A search returns `[]` and the agent says the customer does not exist.
> - An HTTP `DELETE` returns 204 with no body and the agent reports it deleted the record, without any evidence that it did.
> - An MCP server returns `isError: true` with some text and the agent reads the error text as the answer.
>
> Schema validation passes in all three cases, because `[]` and an empty body are valid.
>
> ResultSeal is a small Python library (one dependency, no network access) that you call at the tool boundary. You declare what a result must contain to support a claim. It returns the payload or refuses with a stable reason code:
>
> ```python
> contract = resultseal.load_contract("customer_contract.json")
> resultseal.seal({"kind": "json", "source_ref": "crm://customers",
>                  "target_ref": "customer:42", "body": rows}, contract)
> # BlockedObservation: observation blocked as empty: EMPTY_WITHOUT_NOT_FOUND_SENTINEL
> ```
>
> Decisions are deterministic and fingerprinted, so they replay in CI. It ships with fixtures taken from real backends (SQL, Redis, Elasticsearch, DynamoDB, GraphQL, HTTP 404) and with tested examples for LangChain, LangGraph, LlamaIndex, CrewAI, Pydantic-AI, smolagents and AutoGen.
>
> Playground: https://sx4im.github.io/resultseal/
> Repo: https://github.com/sx4im/resultseal
>
> I'd like to hear how you handle this in production agent pipelines, and what failure shapes you have seen that a fixture should cover.

---

## 2. Reddit (`r/LocalLLaMA`, `r/Python`, `r/MachineLearning`)

**Title:**
> HTTP 200 is not an observation: ResultSeal enforces tool observation integrity for AI agents

**Body:**
> If you have built AI agents with tool calling (LangChain, LangGraph, LlamaIndex, CrewAI, Pydantic-AI, smolagents, AutoGen, or raw MCP), you've likely seen this failure mode:
>
> An agent calls a search tool. The tool returns an empty list `[]`. The agent confidently concludes that the item does not exist or fabricates missing fields. Standard Pydantic schema validation passes because `[]` is valid JSON, but the semantic claim is unverified.
>
> We open-sourced **ResultSeal**: https://github.com/sx4im/resultseal
>
> **What it does:**
> It normalizes tool responses (JSON, HTTP, MCP, stdio), checks them against declarative contracts (required fields, not-found sentinels, freshness, target identity, effect evidence), and returns a deterministic sealed or blocked decision with a stable reason code (e.g. `EMPTY_WITHOUT_NOT_FOUND_SENTINEL`, `UNVERIFIED_EFFECT`). In Python, `resultseal.seal(result, contract)` either returns the payload or raises.
>
> - **Install:** `pip install resultseal` (Python 3.11+)
> - **Playground:** https://sx4im.github.io/resultseal/
> - **Open Issues for Contributors:** https://github.com/sx4im/resultseal/issues
>
> Feedback, edge-case fixtures, and PRs welcome!

---

## 3. Pull Request for Awesome MCP (Model Context Protocol)

**Target Repository:** `punkpeye/awesome-mcp-servers` or `appcypher/awesome-mcp-servers`  
**Section:** *Frameworks & Developer Tools* / *Testing & Security*

**Markdown Entry:**
```markdown
- [ResultSeal](https://github.com/sx4im/resultseal) - Deterministic observation-integrity contracts for MCP tool results. Prevents empty, partial, or error-carrying MCP responses from being promoted into factual agent claims.
```

---

## 4. Pull Request for Awesome AI Agents

**Target Repository:** `e2b-dev/awesome-ai-agents` or `Significant-Gravitas/Awesome-AI-Agents`  
**Section:** *Guardrails & Reliability*

**Markdown Entry:**
```markdown
- [ResultSeal](https://github.com/sx4im/resultseal) - Lightweight, deterministic observation-integrity gate that fails-closed on empty, unverified, or source-mismatched tool results in agent loops.
```
