"""Phase 1 smoke tests: package import, version consistency, CLI version command."""

from __future__ import annotations

import resultseal
from resultseal.cli import main


def test_package_imports() -> None:
    assert resultseal.__name__ == "resultseal"


def test_version_is_semver_string() -> None:
    version = resultseal.__version__
    parts = version.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_version_command_exits_zero() -> None:
    exit_code = main(["version"])
    assert exit_code == 0
