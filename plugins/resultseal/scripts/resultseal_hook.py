#!/usr/bin/env python3
"""PostToolUse hook: seal MCP tool results before Claude Code or Codex reads them.

The hook reads the hook event JSON on stdin. A tool is guarded only when the
project holds a contract named after it, for example
``.resultseal/contracts/mcp__crm__get_customer.json``; every other tool call
passes through untouched. A guarded result that does not seal is answered
with ``{"decision": "block", "reason": ...}``, which both hosts show to the
model in place of (Codex) or next to (Claude Code) the raw result.

In hook mode the observation's ``source_ref`` and ``target_ref`` are taken
from the contract, so identity checks cannot fail here; the hook enforces
emptiness, ``isError``, required fields, freshness and effect evidence.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from resultseal import Contract

CONTRACT_DIR = Path(".resultseal") / "contracts"
CONTRACT_SUFFIXES = (".json", ".yaml", ".yml")
UV_REQUIREMENT = "resultseal>=0.3,<1"


def find_contract(event: dict[str, object]) -> Path | None:
    tool_name = event.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__"):
        return None
    if os.sep in tool_name or "/" in tool_name or tool_name.startswith("."):
        return None
    project = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd")
    if not isinstance(project, str) or not project:
        return None
    for suffix in CONTRACT_SUFFIXES:
        candidate = Path(project) / CONTRACT_DIR / f"{tool_name}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def load_hook_contract(path: Path, tool_name: str) -> Contract:
    """Load the contract at *path*; a missing ``source_ref`` or ``target_ref`` is the tool name.

    Both refs only label the decision in hook mode, so a contract written
    just for the hook may omit them. The file is read with ResultSeal's own
    bounded loaders, the same ones ``resultseal.load_contract`` uses.
    """
    from resultseal.contracts import load_contract_data
    from resultseal.limits import Limits
    from resultseal.safeio import load_json, load_yaml

    limits = Limits()
    loader = load_json if path.suffix == ".json" else load_yaml
    doc = loader(path.read_bytes(), limits)
    if isinstance(doc, dict):
        doc.setdefault("source_ref", tool_name)
        doc.setdefault("target_ref", tool_name)
    return load_contract_data(doc, limits)


def adapter_input(event: dict[str, object], source_ref: str, target_ref: str) -> dict[str, object]:
    """Translate the host's MCP ``tool_response`` into a ResultSeal adapter input.

    Codex sends the MCP call result object; Claude Code sends its content
    blocks or a string. Text that holds a JSON object or array is checked as
    that document through the ``json`` adapter.
    """
    response = event.get("tool_response")
    identity: dict[str, object] = {
        "source_ref": source_ref,
        "target_ref": target_ref,
        "tool_name": event["tool_name"],
    }
    if isinstance(event.get("tool_use_id"), str):
        identity["tool_call_id"] = event["tool_use_id"]

    structured: object = None
    is_error = False
    blocks: object = response
    if isinstance(response, dict):
        structured = response.get("structuredContent")
        is_error = response.get("isError") is True
        blocks = response.get("content")
    if isinstance(blocks, str):
        text = blocks
    elif isinstance(blocks, list):
        text = "\n".join(
            block["text"]
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )
    else:
        text = ""

    if is_error or structured is not None:
        mcp: dict[str, object] = {"kind": "mcp", **identity, "isError": is_error}
        if structured is not None:
            mcp["structuredContent"] = structured
        if text:
            mcp["text"] = text
        return mcp
    document = _json_document(text)
    if document is not None:
        return {"kind": "json", **identity, "body": document}
    return {"kind": "mcp", **identity, "isError": False, "text": text}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite constant {value}")


def _json_document(text: str) -> object:
    """The parsed object or array *text* holds, or None.

    Parsed here rather than handed over as a string: a JSON string body is
    bounded as one string (16 KiB) before parsing, while a parsed body is
    bounded per string, depth and node count like any other input.
    """
    if not text.lstrip().startswith(("{", "[")):
        return None
    try:
        document = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return None
    return document if isinstance(document, (dict, list)) else None


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def _cli_interpreter() -> str | None:
    """The Python that runs a ``pipx`` / ``uv tool`` install of the ``resultseal`` CLI."""
    cli = shutil.which("resultseal")
    if cli is None:
        return None
    try:
        with open(cli, "rb") as handle:
            first_line = handle.readline().decode("utf-8", "replace").strip()
    except OSError:
        return None
    interpreter = first_line[2:].strip() if first_line.startswith("#!") else ""
    if not interpreter or " " in interpreter or not os.path.isfile(interpreter):
        return None
    return interpreter


def _runner() -> list[str] | None:
    """A command that reruns this hook where ``resultseal`` is importable, or None.

    An installed ``resultseal`` CLI wins. Otherwise ``uv`` fetches the newest
    compatible release from PyPI into its cache on first use.
    """
    interpreter = _cli_interpreter()
    if interpreter is not None:
        return [interpreter, __file__]
    uv = shutil.which("uv")
    if uv is not None:
        return [uv, "run", "--quiet", "--no-project", "--with", UV_REQUIREMENT, "python", __file__]
    return None


def _delegate(command: list[str], stdin_text: str, tool_name: str) -> None:
    completed = subprocess.run(
        command,
        input=stdin_text,
        capture_output=True,
        text=True,
        env={**os.environ, "RESULTSEAL_HOOK_DELEGATED": "1"},
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()[-1:] or ["no error output"]
        block(
            f"ResultSeal guards {tool_name} but could not run its check "
            f"({detail[0][:200]}). Do not treat this tool result as verified."
        )
        return
    sys.stdout.write(completed.stdout)


def main(stdin_text: str) -> int:
    try:
        event = json.loads(stdin_text)
    except ValueError:
        return 0
    if not isinstance(event, dict) or event.get("hook_event_name") != "PostToolUse":
        return 0
    contract_path = find_contract(event)
    if contract_path is None:
        return 0

    try:
        import resultseal
    except ImportError:
        command = None if os.environ.get("RESULTSEAL_HOOK_DELEGATED") else _runner()
        if command is not None:
            _delegate(command, stdin_text, event["tool_name"])
            return 0
        block(
            f"ResultSeal guards {event['tool_name']} ({contract_path}) but the "
            "resultseal package is not importable by this hook. Install uv "
            "(https://docs.astral.sh/uv/) or run `pipx install resultseal`. Do not "
            "treat this tool result as verified."
        )
        return 0

    try:
        contract = load_hook_contract(contract_path, event["tool_name"])
        result = resultseal.check(
            adapter_input(event, contract.source_ref, contract.target_ref), contract
        )
    except (resultseal.ResultSealError, OSError) as exc:
        block(
            f"ResultSeal could not evaluate {event['tool_name']} against "
            f"{contract_path}: {exc}. Do not treat this tool result as verified."
        )
        return 0

    if not result.sealed:
        codes = ", ".join(result.reason_codes)
        block(
            f"ResultSeal blocked this {event['tool_name']} result as "
            f"{result.truth_state.value} ({codes}) under {contract_path.name}. "
            "It does not support a factual claim: do not report it as found, "
            "absent or done. Retry, query differently, or tell the user the "
            "result could not be verified."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.read()))
