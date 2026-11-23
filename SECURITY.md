# Security Policy

ResultSeal is designed to process untrusted result data locally. Do not put production secrets in fixtures or issue reports. Report a vulnerability privately through [GitHub private vulnerability reporting](https://github.com/sx4im/resultseal/security/advisories/new) rather than opening a public issue with exploit details.

Security-critical behavior includes safe parsing, bounded inputs, path containment, no dynamic execution, no network access, redaction, deterministic decisions, and fail-closed promotion. Security fixes require a regression test and a changelog entry.

