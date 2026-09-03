"""CLI contract tests: commands, exit codes, output stability, safety."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from resultseal import __version__
from resultseal.canonical import decision_fingerprint
from resultseal.cli import _color_verdict, main

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "fixtures"
EXAMPLES = REPO_ROOT / "examples"

CLOCK = "--now=2026-08-21T12:00:00Z"


def test_verdict_color_requires_tty(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    assert _color_verdict("sealed") == "sealed"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert _color_verdict("sealed") == "\033[32msealed\033[0m"
    assert _color_verdict("MISMATCH") == "\033[31mMISMATCH\033[0m"


def test_no_color_disables_verdict_color(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("NO_COLOR", "")
    assert _color_verdict("BLOCKED") == "BLOCKED"


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------- version --



def test_version_exits_zero(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_package_main_execution(capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "argv", ["resultseal", "version"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("resultseal", run_name="__main__")
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == __version__


def test_no_command_prints_usage_exit_2(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err.lower()



# --------------------------------------------------------------- validate --


def test_validate_contract_valid(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    path = write(tmp_path, "c.json", (EXAMPLES / "minimal_contract.json").read_text())
    assert main(["validate", str(path)]) == 0
    assert "valid" in capsys.readouterr().out


@pytest.mark.parametrize(
    "fixture_name", sorted(p.name for p in FIXTURES.glob("*.yaml"))
)
def test_validate_shipped_fixtures(fixture_name: str) -> None:
    assert main(["validate", str(FIXTURES / fixture_name)]) == 0


def test_validate_invalid_contract_exit_2(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = write(
        tmp_path,
        "bad.json",
        json.dumps({"schema_version": "1", "claim_type": "found", "bogus": True}),
    )
    assert main(["validate", str(path)]) == 2


def test_validate_unsafe_yaml_exit_3(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = write(tmp_path, "evil.yaml", "value: !!python/object/apply:os.system []\n")
    assert main(["validate", str(path)]) == 3


def test_validate_missing_file_exit_2(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert main(["validate", str(tmp_path / "nope.json")]) == 2


# ------------------------------------------------------------------ check --

SEALED_CONTRACT = {
    "schema_version": "1",
    "claim_type": "read_complete",
    "required_fields": ["customer_id"],
    "freshness": {"mode": "not_required"},
    "source_ref": "local://db",
    "target_ref": "customer:42",
}


def sealed_case(tmp_path: Path) -> tuple[Path, Path]:
    contract = write(tmp_path, "c.json", json.dumps(SEALED_CONTRACT))
    response = write(
        tmp_path,
        "r.json",
        json.dumps(
            {
                "kind": "json",
                "source_ref": "local://db",
                "target_ref": "customer:42",
                "body": {"customer_id": "42"},
            }
        ),
    )
    return response, contract


def test_check_sealed_exits_zero(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    response, contract = sealed_case(tmp_path)
    code = main(["check", str(response), "--contract", str(contract), CLOCK])
    assert code == 0
    record = json.loads(capsys.readouterr().out)
    assert record["decision"] == "sealed"


def test_check_blocked_exits_one(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response, contract = sealed_case(tmp_path)
    bad = write(
        tmp_path,
        "partial.json",
        json.dumps({"kind": "json", "source_ref": "local://db",
                    "target_ref": "customer:42", "body": {}}),
    )
    assert main(["check", str(bad), "--contract", str(contract), CLOCK]) == 1


def test_check_invalid_invocation_exit_2(tmp_path) -> None:  # type: ignore[no-untyped-def]
    response, _ = sealed_case(tmp_path)
    missing_contract = write(tmp_path, "broken.json", "{not json")
    assert main(["check", str(response), "--contract", str(missing_contract), CLOCK]) == 2


def test_check_unsafe_response_exit_3(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, contract = sealed_case(tmp_path)
    unsafe = write(
        tmp_path,
        "unsafe.yaml",
        (
            "kind: yaml\nsource_ref: local://db\ntarget_ref: customer:42\n"
            "value: \"!!python/object/apply:os.system ['x']\"\n"
        ),
    )
    assert main(["check", str(unsafe), "--contract", str(contract), CLOCK]) == 3


def test_check_markdown_format(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    response, contract = sealed_case(tmp_path)
    code = main(
        ["check", str(response), "--contract", str(contract), CLOCK, "--format", "md"]
    )
    assert code == 0
    assert "## Decision" in capsys.readouterr().out


def test_check_redact(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    response, contract = sealed_case(tmp_path)
    main(
        [
            "check", str(response), "--contract", str(contract),
            CLOCK, "--redact", "source_ref",
        ]
    )
    assert "[REDACTED]" in capsys.readouterr().out


# ----------------------------------------------------------------- replay --


@pytest.mark.parametrize(
    ("name", "expected_code"),
    [
        ("empty-result.yaml", 0),
        ("explicit-not-found.yaml", 0),
        ("partial-response.yaml", 0),
        ("stale-response.yaml", 0),
        ("wrong-target.yaml", 0),
        ("unverified-write.yaml", 0),
        ("no-dispatch-success-claim.yaml", 0),
        ("complete-fresh-result.yaml", 0),
        ("malformed-json.yaml", 0),
    ],
)
def test_replay_matches_expectations(name: str, expected_code: int) -> None:
    assert main(["replay", str(FIXTURES / name), CLOCK]) == expected_code


def test_replay_unsafe_fixture_exits_three() -> None:
    assert main(["replay", str(FIXTURES / "unsafe-input.yaml"), CLOCK]) == 3


def test_replay_mismatch_exits_one(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    raw = (FIXTURES / "empty-result.yaml").read_text(encoding="utf-8").replace(
        "decision: blocked", "decision: sealed"
    )
    path = write(tmp_path, "tampered.yaml", raw)
    assert main(["replay", str(path), CLOCK]) == 1
    assert "MISMATCH" in capsys.readouterr().out


def test_replay_json_deterministic_across_runs(capsys) -> None:  # type: ignore[no-untyped-def]
    args = ["replay", str(FIXTURES / "complete-fresh-result.yaml"), CLOCK, "--format", "json"]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    second = capsys.readouterr().out
    assert first == second != ""


def test_replay_redacted_json_fingerprint_matches_record(capsys) -> None:  # type: ignore[no-untyped-def]
    args = [
        "replay", str(FIXTURES / "complete-fresh-result.yaml"), CLOCK,
        "--format", "json", "--redact", "source_ref",
    ]
    assert main(args) == 0
    record = json.loads(capsys.readouterr().out)
    shown = record.pop("deterministic_fingerprint")
    assert record["source_ref"] == "[REDACTED]"
    assert decision_fingerprint(record) == shown
