// Browser port of ResultSeal's adapters (normalize.py), contract validation
// (models.Contract), and promotion rules (rules.py) for the GitHub Pages
// playground. tests/test_playground.py replays every shipped fixture through
// this file under Node and requires the same decision, truth state, and
// reason codes as the Python engine. Change both together.
"use strict";

const KINDS = ["http_json", "json", "yaml", "mcp", "stdio", "claim_only"];
const CLAIM_TYPES = ["found", "not_found", "read_complete", "effect_observed", "task_complete"];
const FRESHNESS_MODES = ["not_required", "source_version", "max_age_seconds"];
const CONTRACT_KEYS = [
  "schema_version", "claim_type", "required_fields", "freshness", "min_source_version",
  "source_ref", "target_ref", "not_found_sentinel", "effect_evidence_required",
];
const REQUIRED_CONTRACT_KEYS = [
  "schema_version", "claim_type", "required_fields", "freshness", "source_ref", "target_ref",
];

class InputError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const isInt = (v) => typeof v === "number" && Number.isInteger(v);
const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

function loadContract(raw) {
  const invalid = (message) => new InputError("CONTRACT_INVALID", message);
  if (!isObject(raw)) throw invalid("contract must be an object");
  if (raw.schema_version !== "1") throw invalid("unsupported contract schema_version");
  const unknown = Object.keys(raw).filter((k) => !CONTRACT_KEYS.includes(k));
  if (unknown.length) throw invalid("unknown contract fields: " + unknown.sort().join(", "));
  const missing = REQUIRED_CONTRACT_KEYS.filter((k) => !has(raw, k));
  if (missing.length) throw invalid("missing contract fields: " + missing.sort().join(", "));

  const freshness = raw.freshness;
  if (!isObject(freshness)) throw invalid("freshness must be an object");
  if (Object.keys(freshness).some((k) => k !== "mode" && k !== "max_age_seconds")) {
    throw invalid("unknown freshness fields");
  }
  if (!FRESHNESS_MODES.includes(freshness.mode)) throw invalid("freshness.mode is not valid");
  const maxAge = freshness.max_age_seconds ?? null;
  if (maxAge !== null && !isInt(maxAge)) throw invalid("max_age_seconds must be an integer or null");
  if (!CLAIM_TYPES.includes(raw.claim_type)) throw invalid("claim_type is not a declared claim class");

  const fields = raw.required_fields;
  if (!Array.isArray(fields) || fields.some((f) => typeof f !== "string")) {
    throw invalid("required_fields must be an array of strings");
  }
  if (fields.length > 64) throw invalid("required_fields exceeds 64 items");
  if (fields.some((f) => f.length === 0 || f.length > 256)) {
    throw invalid("required_fields entries must be 1..256 characters");
  }

  const optionalString = (key) => {
    const value = raw[key] ?? null;
    if (value !== null && typeof value !== "string") throw invalid(`field '${key}' must be a string or null`);
    if (value === "") throw invalid(`field '${key}' must be non-empty`);
    return value;
  };
  const requiredString = (key) => {
    const value = raw[key];
    if (typeof value !== "string" || value === "") throw invalid(`field '${key}' must be a non-empty string`);
    return value;
  };
  const effect = raw.effect_evidence_required ?? false;
  if (typeof effect !== "boolean") throw invalid("effect_evidence_required must be boolean");

  const contract = {
    claim_type: raw.claim_type,
    required_fields: fields,
    freshness_mode: freshness.mode,
    max_age_seconds: maxAge,
    min_source_version: optionalString("min_source_version"),
    source_ref: requiredString("source_ref"),
    target_ref: requiredString("target_ref"),
    not_found_sentinel: optionalString("not_found_sentinel"),
    effect_evidence_required: effect,
  };
  if (maxAge !== null && (maxAge < 0 || maxAge > 31536000)) throw invalid("max_age_seconds must be 0..31536000");
  if (contract.freshness_mode === "max_age_seconds" && maxAge === null) {
    throw invalid("max_age_seconds is required when mode is max_age_seconds");
  }
  if (contract.freshness_mode !== "max_age_seconds" && maxAge !== null) {
    throw invalid("max_age_seconds is only valid when mode is max_age_seconds");
  }
  if (contract.freshness_mode === "source_version" && !contract.min_source_version) {
    throw invalid("min_source_version is required when mode is source_version");
  }
  return contract;
}

function inferKind(raw) {
  if (raw.kind !== undefined && raw.kind !== null) {
    if (!KINDS.includes(raw.kind)) throw new InputError("SCHEMA_INVALID", "unknown input kind");
    return raw.kind;
  }
  if (["structuredContent", "isError", "outputSchema"].some((k) => has(raw, k))) return "mcp";
  if (["exit_code", "stdout", "stderr"].some((k) => has(raw, k))) return "stdio";
  if (has(raw, "status_code")) return "http_json";
  return "json";
}

// Returns [payload, parseFailed]; mirrors normalize._parse_body.
function parseBody(body) {
  if (body === undefined || body === null || body === "") return [null, false];
  if (typeof body === "string") {
    try {
      return [JSON.parse(body), false];
    } catch (_) {
      return [null, true];
    }
  }
  if (typeof body === "object" || typeof body === "number" || typeof body === "boolean") return [body, false];
  return [null, true];
}

function normalize(raw, nowIso) {
  if (!isObject(raw)) throw new InputError("SCHEMA_INVALID", "tool result must be an object");
  const kind = inferKind(raw);
  const extra = {};
  let transport = "transported";
  let truth = "observed";
  let payload = null;
  let defaults = {};

  if (kind === "http_json") {
    if (!isInt(raw.status_code)) throw new InputError("SCHEMA_INVALID", "status_code must be an integer");
    if (!has(raw, "target_ref")) {
      if (has(raw, "response_target")) raw = { ...raw, target_ref: raw.response_target };
      else if (has(raw, "request_target")) raw = { ...raw, target_ref: raw.request_target };
    }
    if (raw.status_code >= 200 && raw.status_code < 400) {
      const [parsed, failed] = parseBody(raw.body);
      payload = parsed;
      truth = failed ? "parse_error" : "observed";
    } else {
      transport = "transport_error";
      truth = "unknown";
    }
  } else if (kind === "json") {
    const [parsed, failed] = parseBody(raw.body);
    payload = parsed;
    truth = failed ? "parse_error" : "observed";
  } else if (kind === "yaml") {
    throw new InputError("SCHEMA_INVALID", "kind: yaml inputs need the CLI; the playground parses JSON only");
  } else if (kind === "mcp") {
    const structured = raw.structuredContent ?? null;
    payload = structured !== null ? structured : typeof raw.text === "string" ? raw.text : null;
    if (raw.isError === true) extra.protocol_conflict = true;
  } else if (kind === "stdio") {
    if (!isInt(raw.exit_code)) throw new InputError("SCHEMA_INVALID", "exit_code must be an integer");
    const stdout = raw.stdout;
    if (raw.exit_code !== 0) {
      transport = "transport_error";
      truth = "unknown";
    } else if (raw.output_format === "json" && typeof stdout === "string") {
      const [parsed, failed] = parseBody(stdout);
      payload = parsed;
      truth = failed ? "parse_error" : "observed";
    } else if (typeof stdout === "string" && stdout) {
      payload = stdout;
    } else if (stdout !== null && typeof stdout === "object") {
      payload = stdout;
    }
  } else if (kind === "claim_only") {
    transport = "attempted";
    truth = "unknown";
    defaults = { source_ref: "local://claim", target_ref: "unknown-target" };
  }

  const sourceRef = raw.source_ref ?? defaults.source_ref ?? null;
  const targetRef = raw.target_ref ?? defaults.target_ref ?? null;
  if (typeof sourceRef !== "string" || !sourceRef) {
    throw new InputError("SCHEMA_INVALID", "source_ref must be a non-empty string");
  }
  if (typeof targetRef !== "string" || !targetRef) {
    throw new InputError("SCHEMA_INVALID", "target_ref must be a non-empty string");
  }
  const toolName = raw.tool_name ?? "unspecified-tool";
  if (typeof toolName !== "string" || !toolName) {
    throw new InputError("SCHEMA_INVALID", "tool_name must be a non-empty string");
  }
  const evidence = raw.evidence_refs ?? [];
  if (!Array.isArray(evidence) || evidence.some((e) => typeof e !== "string" || !e)) {
    throw new InputError("SCHEMA_INVALID", "evidence_refs must be an array of non-empty strings");
  }
  const sourceVersion = raw.source_version ?? null;
  if (sourceVersion !== null && (typeof sourceVersion !== "string" || !sourceVersion)) {
    throw new InputError("SCHEMA_INVALID", "source_version must be a non-empty string or null");
  }
  const observedAt = raw.observed_at ?? null;
  if (observedAt !== null && (typeof observedAt !== "string" || !observedAt)) {
    throw new InputError("SCHEMA_INVALID", "observed_at must be an ISO-8601 string");
  }
  const metadata = {};
  if (isObject(raw.metadata)) {
    for (const [key, value] of Object.entries(raw.metadata)) {
      if (value === null || typeof value !== "object") metadata[key] = value;
    }
  }
  Object.assign(metadata, extra);

  const envelope = {
    transport_state: transport,
    truth_state: truth,
    source_ref: sourceRef,
    target_ref: targetRef,
    evidence_refs: evidence,
    source_version: sourceVersion,
    observed_at: observedAt ?? nowIso,
    metadata,
  };
  return { envelope, payload };
}

function naturalCompare(left, right) {
  const runs = (s) => s.match(/\d+|\D+/g) || [];
  const a = runs(left);
  const b = runs(right);
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const digits = /^\d+$/.test(a[i]) && /^\d+$/.test(b[i]);
    if (digits) {
      const x = BigInt(a[i]);
      const y = BigInt(b[i]);
      if (x !== y) return x < y ? -1 : 1;
    } else if (a[i] !== b[i]) {
      return a[i] < b[i] ? -1 : 1;
    }
  }
  if (a.length !== b.length) return a.length < b.length ? -1 : 1;
  return 0;
}

// Offset-aware ISO-8601 only, like rules._parse_timestamp: a naive timestamp
// cannot be compared to the reference clock and is refused.
function parseTimestamp(value) {
  if (!/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/.test(value)) return null;
  const ms = Date.parse(value.replace(" ", "T"));
  return Number.isNaN(ms) ? null : ms;
}

const unusable = (p) =>
  p === null || p === "" || (Array.isArray(p) && p.length === 0) || (isObject(p) && Object.keys(p).length === 0);

function sentinelMatched(payload, sentinel) {
  if (sentinel === null) return false;
  if (payload === sentinel) return true;
  return isObject(payload) && Object.values(payload).some((v) => v === sentinel);
}

const verdict = (decision, truth_state, reason_codes) => ({ decision, truth_state, reason_codes });

function evaluate(envelope, payload, contract, nowMs) {
  const blocked = (truth, ...codes) => verdict("blocked", truth, codes);
  if (envelope.transport_state === "attempted" || envelope.transport_state === "dispatched") {
    return blocked("unknown", "NO_DISPATCH");
  }
  if (envelope.transport_state === "transport_error") return blocked("unknown", "TRANSPORT_FAILED");
  if (envelope.truth_state === "parse_error") return blocked("parse_error", "PARSE_FAILED");
  if (envelope.metadata.protocol_conflict === true) return blocked("unknown", "PROTOCOL_CONFLICT");

  const matched = sentinelMatched(payload, contract.not_found_sentinel);
  if (contract.claim_type === "not_found" && !matched) {
    return blocked(unusable(payload) ? "empty" : "observed", "EMPTY_WITHOUT_NOT_FOUND_SENTINEL");
  }
  if (unusable(payload) && !matched) return blocked("empty", "EMPTY_WITHOUT_NOT_FOUND_SENTINEL");

  const identity = [];
  if (envelope.source_ref !== contract.source_ref) identity.push("SOURCE_MISMATCH");
  if (envelope.target_ref !== contract.target_ref) identity.push("TARGET_MISMATCH");
  if (identity.length) return blocked("source_mismatch", ...identity);

  if (contract.freshness_mode === "source_version") {
    if (!envelope.source_version) return blocked("unknown", "MISSING_REQUIRED_FIELD", "STALE_OBSERVATION");
    if (naturalCompare(envelope.source_version, contract.min_source_version) < 0) {
      return blocked("stale", "STALE_OBSERVATION");
    }
  } else if (contract.freshness_mode === "max_age_seconds") {
    const observed = parseTimestamp(envelope.observed_at);
    if (observed === null) return blocked("unknown", "SCHEMA_INVALID");
    const age = (nowMs - observed) / 1000;
    if (age < 0 || age > contract.max_age_seconds) return blocked("stale", "STALE_OBSERVATION");
  }

  if (contract.required_fields.some((name) => !isObject(payload) || !has(payload, name))) {
    return blocked("partial", "MISSING_REQUIRED_FIELD");
  }
  if (
    (contract.claim_type === "effect_observed" || contract.claim_type === "task_complete") &&
    contract.effect_evidence_required &&
    envelope.evidence_refs.length === 0
  ) {
    return blocked("unverified_effect", "UNVERIFIED_EFFECT");
  }
  const sealedTruth = contract.claim_type === "not_found" ? "not_found" : "sealed";
  return verdict("sealed", sealedTruth, ["SEALED_WITH_REQUIRED_EVIDENCE"]);
}

// The playground's single entrypoint. Returns a verdict, or {error, message}
// for input the CLI would reject with exit code 2.
function evaluateObservation(raw, rawContract, now = new Date()) {
  try {
    const contract = loadContract(rawContract);
    const nowIso = now.toISOString().replace(/\.\d{3}Z$/, "Z");
    const { envelope, payload } = normalize(raw, nowIso);
    return evaluate(envelope, payload, contract, now.getTime());
  } catch (err) {
    if (err instanceof InputError) return { error: err.code, message: err.message };
    throw err;
  }
}

const PRESETS = {
  empty_sql: {
    label: "Empty SQL result",
    expect: "blocked",
    raw: {
      kind: "json",
      source_ref: "db://users",
      target_ref: "users:email:alice@example.com",
      tool_name: "sql_query",
      body: [],
    },
    contract: {
      schema_version: "1",
      claim_type: "found",
      required_fields: ["user_id", "email"],
      freshness: { mode: "not_required" },
      source_ref: "db://users",
      target_ref: "users:email:alice@example.com",
    },
  },
  valid_mcp: {
    label: "Complete MCP result",
    expect: "sealed",
    raw: {
      source_ref: "mcp://crm-server",
      target_ref: "customer:42",
      tool_name: "get_customer",
      structuredContent: { customer_id: "42", name: "Ada Lovelace", status: "active" },
      outputSchema: { type: "object", required: ["customer_id", "name"] },
      isError: false,
    },
    contract: {
      schema_version: "1",
      claim_type: "read_complete",
      required_fields: ["customer_id", "name"],
      freshness: { mode: "not_required" },
      source_ref: "mcp://crm-server",
      target_ref: "customer:42",
    },
  },
  http_empty: {
    label: "HTTP 200, empty body",
    expect: "blocked",
    raw: {
      kind: "http_json",
      status_code: 200,
      source_ref: "https://api.crm.internal/v1",
      target_ref: "customer:42",
      body: "",
    },
    contract: {
      schema_version: "1",
      claim_type: "not_found",
      required_fields: [],
      freshness: { mode: "not_required" },
      source_ref: "https://api.crm.internal/v1",
      target_ref: "customer:42",
      not_found_sentinel: "NOT_FOUND",
    },
  },
  http_404: {
    label: "HTTP 404 with error body",
    expect: "blocked",
    raw: {
      kind: "http_json",
      status_code: 404,
      source_ref: "https://api.crm.internal/v1",
      target_ref: "customer:42",
      body: { error: "not_found", message: "Customer 42 not found" },
    },
    contract: {
      schema_version: "1",
      claim_type: "not_found",
      required_fields: [],
      freshness: { mode: "not_required" },
      source_ref: "https://api.crm.internal/v1",
      target_ref: "customer:42",
      not_found_sentinel: "not_found",
    },
  },
  mcp_error: {
    label: "MCP isError with text",
    expect: "blocked",
    raw: {
      kind: "mcp",
      source_ref: "mcp://tools",
      target_ref: "user:admin",
      isError: true,
      text: "Permission denied",
    },
    contract: {
      schema_version: "1",
      claim_type: "found",
      required_fields: [],
      freshness: { mode: "not_required" },
      source_ref: "mcp://tools",
      target_ref: "user:admin",
    },
  },
  stale_revision: {
    label: "Stale cached revision",
    expect: "blocked",
    raw: {
      kind: "json",
      source_ref: "cache://orders",
      target_ref: "order:991",
      source_version: "revision-9",
      body: { order_id: "991", status: "shipped" },
    },
    contract: {
      schema_version: "1",
      claim_type: "read_complete",
      required_fields: ["order_id", "status"],
      freshness: { mode: "source_version" },
      min_source_version: "revision-12",
      source_ref: "cache://orders",
      target_ref: "order:991",
    },
  },
  sentinel_found: {
    label: "Explicit not-found sentinel",
    expect: "sealed",
    raw: {
      kind: "json",
      source_ref: "fixture://directory",
      target_ref: "customer:42",
      body: { status: "NOT_FOUND" },
    },
    contract: {
      schema_version: "1",
      claim_type: "not_found",
      required_fields: [],
      freshness: { mode: "not_required" },
      source_ref: "fixture://directory",
      target_ref: "customer:42",
      not_found_sentinel: "NOT_FOUND",
    },
  },
};

if (typeof module !== "undefined") {
  module.exports = { evaluateObservation, PRESETS };
}
