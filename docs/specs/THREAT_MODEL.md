# Threat Model

## Assets

The main assets are the integrity of the promotion decision, user data embedded in tool results, local credentials, filesystem boundaries, CI execution, and developer trust in reports.

## Threats and controls

| Threat | Required control |
|---|---|
| Unsafe YAML tags or object construction | Safe parser only; reject tags and custom constructors. |
| Path traversal | Resolve paths under an allowed root and reject escapes. |
| Dynamic code execution | No `eval`, `exec`, plugin imports, templates, or shell commands. |
| Network exfiltration | Core package has no network behavior; adapters accept values, not URLs to fetch. |
| Secret leakage | Redact configured secret patterns; never include environment or headers by default. |
| Resource exhaustion | Enforce size, depth, collection, and report limits. |
| Result poisoning | Preserve source/target identity and require explicit evidence. |
| False promotion | Fail closed for unknown, empty, partial, stale, and unverified states. |
| Nondeterministic reports | Stable ordering, injectable clock, deterministic fingerprints. |

The threat model does not claim to secure the external tool or database. It protects the local evaluation and promotion boundary.

