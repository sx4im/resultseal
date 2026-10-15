"""README code must run: every ```python block executes, top to bottom.

Lines written as ``<expression>  # -> <literal>`` are also evaluated and
compared with the literal, so the documented results cannot drift.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
BLOCKS = re.findall(r"```python\n(.*?)```", README, flags=re.DOTALL)
CLAIM = re.compile(r"^(?P<expr>\S.*?)\s+# -> (?P<expected>.+)$")


def _claims(block: str) -> list[tuple[str, object]]:
    claims = []
    for line in block.splitlines():
        match = CLAIM.match(line)
        if match is None:
            continue
        try:
            expected = ast.literal_eval(match["expected"])
        except (ValueError, SyntaxError):
            continue  # not a literal, e.g. an enum member
        claims.append((match["expr"], expected))
    return claims


def test_readme_has_python_examples() -> None:
    assert len(BLOCKS) >= 4


def test_readme_python_blocks_run_and_their_results_hold(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    namespace: dict[str, object] = {}
    checked = 0
    for block in BLOCKS:
        exec(compile(block, "README.md", "exec"), namespace)
        for expression, expected in _claims(block):
            assert eval(expression, namespace) == expected, expression
            checked += 1
    assert checked >= 4
    assert "observation blocked as empty: EMPTY_WITHOUT_NOT_FOUND_SENTINEL" in (
        capsys.readouterr().out
    )
