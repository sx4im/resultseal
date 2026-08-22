# Contract File Contract

Contracts are declarative data. The MVP format supports JSON and, only when a safe parser is available, a restricted YAML representation.

A contract declares `schema_version`, `claim_type`, required fields, permitted source patterns, target matching rules, freshness policy, not-found sentinel rules, and effect-evidence requirements. Unsupported keys must be rejected or clearly ignored according to the versioning policy; silently changing semantics is forbidden.

Contracts must be bounded by file size, nesting depth, collection length, string length, and total input count. They must not contain executable expressions, anchors that cause expansion abuse, custom tags, imports, includes, remote references, or secrets.

