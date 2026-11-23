"""The Claude Code / Codex plugin under plugins/resultseal.

The hook is driven the way both hosts drive it: one PostToolUse event as JSON
on stdin, a block decision as JSON on stdout, exit code 0 either way.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN = REPO_ROOT / "plugins" / "resultseal"
HOOK = PLUGIN / "scripts" / "resultseal_hook.py"
TOOL = "mcp__crm__get_customer"

CONTRACT = {
    "schema_version": "1",
    "claim_type": "found",
    "required_fields": ["customer_id", "name"],
    "freshness": {"mode": "not_required"},
    "source_ref": "mcp://crm",
    "target_ref": "crm:customer",
}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    contracts = tmp_path / ".resultseal" / "contracts"
    contracts.mkdir(parents=True)
    (contracts / f"{TOOL}.json").write_text(json.dumps(CONTRACT), encoding="utf-8")
    return tmp_path


def run_hook(project: Path, tool_response: object, tool_name: str = TOOL) -> dict[str, object]:
    event = {
        "hook_event_name": "PostToolUse",
        "cwd": str(project),
        "tool_name": tool_name,
        "tool_input": {"customer_id": "42"},
        "tool_response": tool_response,
        "tool_use_id": "toolu_01",
    }
    completed = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "", "CLAUDE_PROJECT_DIR": str(project)},
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


def text_blocks(value: object) -> list[dict[str, str]]:
    return [{"type": "text", "text": json.dumps(value)}]


def test_empty_claude_result_is_blocked(project: Path) -> None:
    output = run_hook(project, text_blocks([]))
    assert output["decision"] == "block"
    assert "EMPTY_WITHOUT_NOT_FOUND_SENTINEL" in str(output["reason"])


def test_complete_json_text_passes_silently(project: Path) -> None:
    assert run_hook(project, text_blocks({"customer_id": "42", "name": "Ada"})) == {}


def test_codex_structured_content_missing_field_is_blocked(project: Path) -> None:
    response = {"content": [], "structuredContent": {"customer_id": "42"}, "isError": False}
    output = run_hook(project, response)
    assert "MISSING_REQUIRED_FIELD" in str(output["reason"])


def test_codex_structured_content_complete_passes(project: Path) -> None:
    response = {
        "content": [{"type": "text", "text": "Ada"}],
        "structuredContent": {"customer_id": "42", "name": "Ada"},
        "isError": False,
    }
    assert run_hook(project, response) == {}


def test_is_error_result_is_blocked(project: Path) -> None:
    response = {"content": [{"type": "text", "text": "upstream timeout"}], "isError": True}
    output = run_hook(project, response)
    assert "PROTOCOL_CONFLICT" in str(output["reason"])


def test_plain_text_result_cannot_satisfy_required_fields(project: Path) -> None:
    output = run_hook(project, "No customer found")
    assert "MISSING_REQUIRED_FIELD" in str(output["reason"])


def test_json_text_over_one_string_limit_is_checked_as_a_document(project: Path) -> None:
    rows = [{"customer_id": str(i), "name": "Ada Lovelace " * 20} for i in range(80)]
    record = {"customer_id": "42", "name": "Ada", "history": rows}
    assert len(json.dumps(record)) > 16_384
    assert run_hook(project, text_blocks(record)) == {}


def test_not_found_sentinel_seals_absence(project: Path) -> None:
    contract = {**CONTRACT, "claim_type": "not_found", "required_fields": [],
                "not_found_sentinel": "NOT_FOUND"}
    path = project / ".resultseal" / "contracts" / "mcp__crm__find_customer.yaml"
    path.write_text(json.dumps(contract), encoding="utf-8")
    sealed = run_hook(project, text_blocks({"status": "NOT_FOUND"}), "mcp__crm__find_customer")
    assert sealed == {}
    blocked = run_hook(project, text_blocks([]), "mcp__crm__find_customer")
    assert "EMPTY_WITHOUT_NOT_FOUND_SENTINEL" in str(blocked["reason"])


def test_invalid_contract_blocks_instead_of_passing(project: Path) -> None:
    path = project / ".resultseal" / "contracts" / "mcp__crm__broken.json"
    path.write_text('{"schema_version": "1"}', encoding="utf-8")
    output = run_hook(project, text_blocks({"customer_id": "42"}), "mcp__crm__broken")
    assert output["decision"] == "block"
    assert "could not evaluate" in str(output["reason"])


@pytest.mark.parametrize(
    "tool_name", ["mcp__crm__list_customers", "Bash", "mcp__../../etc/passwd"]
)
def test_tools_without_a_contract_are_untouched(project: Path, tool_name: str) -> None:
    assert run_hook(project, [], tool_name) == {}


def test_other_events_are_ignored(project: Path) -> None:
    event = {"hook_event_name": "PreToolUse", "cwd": str(project), "tool_name": TOOL}
    completed = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(event),
        capture_output=True, text=True, check=False,
    )
    assert (completed.returncode, completed.stdout) == (0, "")


def load(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_manifests_and_marketplaces_agree() -> None:
    claude = load(PLUGIN / ".claude-plugin" / "plugin.json")
    codex = load(PLUGIN / ".codex-plugin" / "plugin.json")
    assert claude["name"] == codex["name"] == "resultseal"
    assert claude["version"] == codex["version"]

    codex_market_path = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
    if not codex_market_path.exists():
        pytest.skip("source archives exclude .agents/")
    claude_market = load(REPO_ROOT / ".claude-plugin" / "marketplace.json")
    codex_market = load(codex_market_path)
    [claude_entry] = claude_market["plugins"]  # type: ignore[misc]
    [codex_entry] = codex_market["plugins"]  # type: ignore[misc]
    assert claude_entry["name"] == codex_entry["name"] == "resultseal"
    assert (REPO_ROOT / claude_entry["source"]).resolve() == PLUGIN
    assert (REPO_ROOT / codex_entry["source"]["path"]).resolve() == PLUGIN


def test_hook_config_runs_the_bundled_script() -> None:
    config = load(PLUGIN / "hooks" / "hooks.json")
    [entry] = config["hooks"]["PostToolUse"]  # type: ignore[index]
    assert entry["matcher"] == "mcp__.*"
    command = entry["hooks"][0]["command"]
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/resultseal_hook.py" in command


def test_skill_front_matter_names_its_directory() -> None:
    skill = PLUGIN / "skills" / "resultseal-contracts" / "SKILL.md"
    front = re.match(r"---\n(.*?)\n---\n", skill.read_text(encoding="utf-8"), re.DOTALL)
    assert front is not None
    assert "name: resultseal-contracts" in front.group(1)
    assert "description: " in front.group(1)
