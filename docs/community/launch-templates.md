# Sharing ResultSeal

Use a runnable example and describe the checks it performs. A seal means the
contract passed; it cannot establish that a remote source or model is honest.
The [discovery plan](discovery-plan.md) tracks audiences, rollout and measurement.
These drafts have not been posted.

## X or Mastodon draft

> An empty tool result can become a confident answer in an agent loop.
>
> ResultSeal checks tool output against a contract before returning it to the
> model. Empty results block; explicit absence needs an approved sentinel.
>
> Python, offline, JSON/HTTP/MCP/stdio.
> https://github.com/sx4im/resultseal

Attach a short recording of the playground: empty SQL result, complete MCP
result, then the same result with a required field removed. Keep the actual
reason codes visible. Add captions so the example works without audio.

## LinkedIn draft

> A CRM lookup returns []. An agent can turn that empty result into a claim
> that the customer does not exist, even when the lookup was incomplete.
>
> ResultSeal makes that decision explicit. The Python library checks required
> fields, source and target identity, freshness, absence sentinels and effect
> evidence against a per-tool contract. `seal()` returns the payload when those
> checks pass and raises `BlockedObservation` otherwise.
>
> It runs locally without model calls. The repository includes examples for
> LangChain, LangGraph, LlamaIndex, CrewAI, Pydantic-AI, smolagents and AutoGen.
>
> Try the playground: https://sx4im.github.io/resultseal/
> Code: https://github.com/sx4im/resultseal
>
> Which tool response has caused an incorrect conclusion in your workflow?

Replace the opening with a real incident if you have one you can share. Avoid
claiming deployment experience or measured improvements without evidence.

## Hacker News preparation

Write the submission and comments yourself. HN's current guidelines prohibit
generated or AI-edited text and automated posting. The previous ready-to-paste
HN intro has been removed.

Facts to check before deciding whether to submit:

- The playground works without an account, and installation works in a clean venv.
- You can explain the difference between shape validation and a promotion contract.
- You can demonstrate a blocked observation and name what a seal does not prove.
- You can be present to discuss the implementation and its limitations.
- Search for earlier submissions. A routine version bump does not qualify as
  a new Show HN; follow the rules on substantial changes and reposting.

Sources: [Show HN](https://news.ycombinator.com/showhn.html),
[HN guidelines](https://news.ycombinator.com/newsguidelines.html).

## Reddit and framework communities

Choose one community where people discuss tool-result handling. Read its current
rules, flair requirements and pinned showcase thread before posting; a general
Python audience and a local-model audience have different interests. Disclose
that you maintain the project. Show the failing response, the contract, the
blocked result and a limitation. Ask for a response shape to turn into a fixture.

Use the relevant framework example as the starting point. Answer technical
questions in the thread. Avoid copying one announcement across unrelated groups.

## Directory entry

Use only when a directory accepts libraries or developer tools and its rules
permit the submission. Check the category and contribution rules first.

```markdown
- [ResultSeal](https://github.com/sx4im/resultseal) - Python contracts that check JSON, HTTP, MCP and stdio tool results before they support agent claims. Includes guards for empty, partial, stale and unverified observations.
```

ResultSeal is a library, so server-only MCP lists are a poor fit. In particular,
[Awesome MCP Servers' contribution rules](https://github.com/punkpeye/awesome-mcp-servers/blob/main/CONTRIBUTING.md)
limit the list to installable servers. A LangChain tools list is a candidate
because the repository contains a LangChain example; inclusion still depends on
that list's scope and maintainer review.
