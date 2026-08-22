# Contributing

Keep changes narrow and evidence-driven. A contribution should state the failure mode it addresses, include a regression test or fixture, preserve determinism, and update relevant protocol or CLI documentation. New adapters must not convert transport success into semantic success. Do not add network access, dynamic execution, or hidden model calls.

Before opening a pull request, run the documented test, lint, type, and build commands. Include exact results and explain any platform-specific behavior.

