## What

One line describing the change.

## Failure mode addressed

Link the issue, or state the failure mode: what was promoted, blocked, classified, or reported incorrectly?

## Tests

- [ ] Regression test or fixture included

## Determinism

- [ ] Decisions stay deterministic given identical inputs and a pinned reference clock
- [ ] Reports and fingerprints carry no wall-clock values

## Gates

Exact results from the documented commands:

```
ruff check src tests:
mypy src:
pytest:
```

## Docs

- [ ] Relevant specs under `docs/specs/` updated if behavior changed
- [ ] `docs/decision-log.md` entry added if a documented invariant changed
