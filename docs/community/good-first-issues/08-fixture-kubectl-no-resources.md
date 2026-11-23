---
title: "Add `kubectl get` \"No resources found\" stdio fixture"
labels: enhancement, help wanted, good first issue
---

### Problem

`kubectl get pods -l app=api` with no matching pods exits 0, prints nothing
on stdout and writes `No resources found in default namespace.` to stderr.
Coding agents run kubectl constantly, and exit code 0 plus empty stdout
reads as "there are no API pods", even when the selector, namespace or
context is wrong. ResultSeal blocks it as empty; there is no stdio fixture
for a real CLI yet.

### Desired implementation

Create `fixtures/kubectl-no-resources.yaml`:

1. `name: kubectl-no-resources`, `claim_type: found`
2. Contract with `required_fields: []`,
   `source_ref: k8s://default/pods` and `target_ref: pods:app=api`
3. Input:
   - `kind: stdio`, `exit_code: 0`
   - `command: kubectl get pods -l app=api`
   - `stdout: ""`
   - `stderr: "No resources found in default namespace.\n"`
   - matching `source_ref` / `target_ref`, `tool_name: kubectl_get_pods`
4. Expected outcome:
   - `decision: blocked`
   - `truth_state: empty`
   - `reason_codes: [EMPTY_WITHOUT_NOT_FOUND_SENTINEL]`
5. Add a row to the "Real-world backends" table in
   `docs/specs/FIXTURE_CATALOG.md`.

The stdio adapter is described in `docs/specs/ADAPTERS.md`, and its tests
in `tests/test_normalize_stdio.py` show the input shape.

### Verification

```bash
resultseal replay fixtures/kubectl-no-resources.yaml   # MATCH: kubectl-no-resources -> empty/blocked
pytest tests/test_fixture_matrix.py tests/test_cli.py
ruff check .
mypy src
```
