---
name: Framework Integration Example
about: Add a runnable agent framework tool-guard example under examples/
labels: ["documentation", "enhancement", "good first issue"]
---

### Framework
What framework is being integrated (e.g., LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex)?

### Pattern
- Where is the tool result intercepted before returning to the model?
- What contract does it validate against?

### Checklist
- [ ] Added runnable example script in `examples/<framework>_tool_guard.py`
- [ ] Added dependency-free test in `tests/test_examples.py`
- [ ] No required heavy dependencies added to core `pyproject.toml`
