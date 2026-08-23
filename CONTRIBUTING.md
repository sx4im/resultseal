# Contributing

Keep changes narrow and evidence-driven. A contribution should state the failure mode it addresses, include a regression test or fixture, preserve determinism, and update relevant protocol or CLI documentation. New adapters must not convert transport success into semantic success. Do not add network access, dynamic execution, or hidden model calls.

A change that touches a documented invariant — a promotion rule, an error code, a schema field, an adapter behavior — adds a new dated entry to [docs/decision-log.md](docs/decision-log.md): a `## D<number> — <date> — <title>` heading after the last entry, followed by a concise statement of what was decided and why, in the style of the existing entries. The log is append-only; a superseded decision is corrected by a newer entry, never by rewriting an old one.

Before opening a pull request, run the documented test, lint, type, and build commands. Include exact results and explain any platform-specific behavior.

