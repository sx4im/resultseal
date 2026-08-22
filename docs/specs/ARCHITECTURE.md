# Architecture

```text
raw tool result
      |
      v
normalizer -----> bounded metadata + parsed observation
      |
      v
ObservationEnvelope
      |
      v
pure promotion rules <----- Contract
      |
      +---- sealed / blocked / unknown
      |
      v
deterministic report and stable CLI exit code
```

## Modules

| Module | Responsibility | Must not do |
|---|---|---|
| `models.py` | Typed enums and immutable envelope models | Perform I/O or policy decisions |
| `normalize.py` | Convert HTTP, MCP, and stdio inputs | Declare semantic success merely from transport status |
| `rules.py` | Pure promotion and reason-code logic | Call network services or models |
| `contracts.py` | Load and validate declarative contracts | Evaluate arbitrary expressions |
| `fixtures.py` | Safe bounded fixture loading | Follow imports, URLs, or code |
| `report.py` | Stable JSON/Markdown output | Add nondeterministic timestamps by default |
| `cli.py` | User-facing commands and exit codes | Hide failures or swallow exceptions |

## Data flow invariant

Every result starts as untrusted raw input. Normalization may establish structural facts. Only the pure rules engine may determine eligibility. A `sealed` result must contain the reason and evidence references that made it eligible. A model-generated claim is metadata only.

## Dependency policy

Prefer the standard library. Every non-standard dependency requires a documented reason, license check, security review, and offline installation test. No dependency may be used to execute user-provided code.

