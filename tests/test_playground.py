"""The GitHub Pages playground (docs/playground.js) must agree with the engine.

Every shipped fixture and every playground preset is evaluated by both the
JavaScript port (under Node) and ``resultseal.check``; decision, truth state,
and reason codes must be identical. Skipped when Node is not installed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

import resultseal
from resultseal.errors import ResultSealError
from resultseal.limits import Limits
from resultseal.safeio import load_yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAYGROUND = REPO_ROOT / "docs" / "playground.js"
NOW = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

_RUNNER = """
const { evaluateObservation, PRESETS } = require(process.argv[1]);
const cases = JSON.parse(require("fs").readFileSync(0, "utf8"));
const now = new Date(process.argv[2]);
const results = cases.map(([raw, contract]) => evaluateObservation(raw, contract, now));
process.stdout.write(JSON.stringify({ results, presets: PRESETS }));
"""


def _run_node(cases: list[tuple[object, object]]) -> dict[str, object]:
    assert NODE is not None
    completed = subprocess.run(
        [NODE, "-e", _RUNNER, str(PLAYGROUND), NOW.isoformat()],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
    )
    output: dict[str, object] = json.loads(completed.stdout)
    return output


def _python_verdict(raw: dict[str, object], contract: dict[str, object]) -> dict[str, object]:
    try:
        result = resultseal.check(raw, resultseal.load_contract(contract), now=NOW)
    except ResultSealError as exc:
        return {"error": exc.code}
    return {
        "decision": result.decision.value,
        "truth_state": result.truth_state.value,
        "reason_codes": list(result.reason_codes),
    }


def _js_verdict(result: dict[str, object]) -> dict[str, object]:
    return {"error": result["error"]} if "error" in result else result


def _fixture_cases() -> list[tuple[str, dict[str, object], dict[str, object]]]:
    cases = []
    for path in sorted((REPO_ROOT / "fixtures").glob("*.yaml")):
        doc = load_yaml(path.read_bytes(), Limits())
        assert isinstance(doc, dict)
        contract, raw = doc.get("contract"), doc["input"]
        assert isinstance(raw, dict)
        if contract is None or raw.get("kind") == "yaml":
            continue  # nested-YAML inputs are CLI-only in the playground
        assert isinstance(contract, dict)
        cases.append((path.name, raw, contract))
    return cases


EDGE_CASES: list[tuple[str, dict[str, object], dict[str, object]]] = [
    (
        "missing-required-fields-key",
        {"kind": "json", "source_ref": "s", "target_ref": "t", "body": {"a": 1}},
        {"schema_version": "1", "claim_type": "found",
         "freshness": {"mode": "not_required"}, "source_ref": "s", "target_ref": "t"},
    ),
    (
        "naive-timestamp-under-max-age",
        {"kind": "json", "source_ref": "s", "target_ref": "t", "body": {"a": 1},
         "observed_at": "2026-08-21T11:59:30"},
        {"schema_version": "1", "claim_type": "found", "required_fields": ["a"],
         "freshness": {"mode": "max_age_seconds", "max_age_seconds": 60},
         "source_ref": "s", "target_ref": "t"},
    ),
    (
        "fresh-timestamp-under-max-age",
        {"kind": "json", "source_ref": "s", "target_ref": "t", "body": {"a": 1},
         "observed_at": "2026-08-21T11:59:30Z"},
        {"schema_version": "1", "claim_type": "found", "required_fields": ["a"],
         "freshness": {"mode": "max_age_seconds", "max_age_seconds": 60},
         "source_ref": "s", "target_ref": "t"},
    ),
    (
        "stdio-nonzero-exit",
        {"exit_code": 2, "stdout": "{}", "source_ref": "s", "target_ref": "t"},
        {"schema_version": "1", "claim_type": "found", "required_fields": [],
         "freshness": {"mode": "not_required"}, "source_ref": "s", "target_ref": "t"},
    ),
    (
        "effect-without-evidence",
        {"kind": "json", "source_ref": "s", "target_ref": "t", "body": {"status": 204}},
        {"schema_version": "1", "claim_type": "effect_observed", "required_fields": ["status"],
         "freshness": {"mode": "not_required"}, "source_ref": "s", "target_ref": "t",
         "effect_evidence_required": True},
    ),
]


def test_playground_matches_engine_on_fixtures_and_edge_cases() -> None:
    cases = _fixture_cases() + EDGE_CASES
    output = _run_node([(raw, contract) for _, raw, contract in cases])
    results = output["results"]
    assert isinstance(results, list)
    for (name, raw, contract), js_result in zip(cases, results, strict=True):
        assert _js_verdict(js_result) == _python_verdict(raw, contract), name


def test_playground_presets_match_engine_and_their_labels() -> None:
    presets = _run_node([])["presets"]
    assert isinstance(presets, dict) and presets
    cases = [(p["raw"], p["contract"]) for p in presets.values()]
    results = _run_node(cases)["results"]
    assert isinstance(results, list)
    for (key, preset), js_result in zip(presets.items(), results, strict=True):
        engine = _python_verdict(preset["raw"], preset["contract"])
        assert _js_verdict(js_result) == engine, key
        assert engine.get("decision") == preset["expect"], key
