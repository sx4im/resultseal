---
name: Feature request
about: A capability within ResultSeal's scope
labels: enhancement
---

**Problem to solve**

What observation-integrity failure mode or workflow does this address? Check [docs/specs/NON_GOALS.md](../blob/master/docs/specs/NON_GOALS.md) first — agent frameworks, proxies, dashboards, policy engines, retry middleware, signed receipts, and LLM judges are out of scope.

**Proposed behavior**

What should the new capability do, and how does it fit the existing contract → normalize → evaluate pipeline?

**Determinism impact**

Confirm the feature keeps decisions byte-deterministic given identical inputs and a pinned reference clock, and justify any new dependency.
