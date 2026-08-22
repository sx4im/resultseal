# Product Specification

## Problem

Tool-using agents and workflow systems often collapse transport status, parsed output, semantic completeness, freshness, target identity, and real-world effect into one binary success value. This lets empty or partial observations become confident factual claims.

## Product promise

ResultSeal gives developers a deterministic, framework-neutral way to decide whether a tool observation is eligible to support a downstream claim. It does not judge language quality or prove all real-world truth; it enforces explicit evidence-promotion rules at a tool-result boundary.

## Primary users

The first users are developers building MCP servers, HTTP tools, CLI tools, coding-agent integrations, and workflow automations. They should be able to use ResultSeal without adopting an agent framework or sending data to a hosted service.

## MVP features

| Feature | Required behavior |
|---|---|
| Typed observation envelope | Versioned, JSON-serializable representation separating transport and semantic truth. |
| Pure promotion rules | Deterministic sealing decision with explicit reason codes. |
| Three normalizers | Generic HTTP/JSON, MCP-style, and stdio/CLI inputs. |
| Offline negative-test runner | Reproducible fixtures for empty, partial, stale, wrong-target, unverified, and valid results. |
| CI-friendly CLI | Stable commands, exit codes, Markdown/JSON reports, no model or network dependency. |

## Success criteria

A new user can install ResultSeal, run the empty-result fixture, see why `empty` cannot become `not_found`, run the explicit not-found fixture, and obtain a passing seal in under five minutes. All outputs are deterministic across repeated runs.

## Explicit non-goals

ResultSeal is not a proxy, dashboard, policy engine, receipt standard, authorization service, retry manager, LLM judge, agent orchestrator, database verifier, or universal MCP test platform.

