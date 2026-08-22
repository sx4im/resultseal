"""Purity and safety scans: rules core must stay free of I/O and dangerous APIs."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "resultseal"

PURE_MODULES = frozenset({"models.py", "canonical.py", "rules.py"})
PURE_ALLOWED_IMPORTS = frozenset(
    {
        "__future__",
        "collections",
        "collections.abc",
        "dataclasses",
        "datetime",
        "enum",
        "functools",
        "hashlib",
        "itertools",
        "json",
        "re",
        "types",
        "typing",
        "resultseal.errors",
        "resultseal.models",
    }
)
FORBIDDEN_CALLS = frozenset(
    {"eval", "exec", "compile", "__import__", "open", "os.system", "os.popen"}
)
# Forbidden everywhere. os/sys are additionally barred from pure modules via
# PURE_ALLOWED_IMPORTS; the CLI layer is the sanctioned I/O boundary.
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {"subprocess", "socket", "urllib", "http", "requests", "importlib"}
)


def _imports_and_calls(tree: ast.AST) -> tuple[set[str], set[str]]:
    imported: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.add(func.id)
            elif isinstance(func, ast.Attribute):
                # Flag dangerous attribute calls only on known-dangerous
                # bases (e.g. os.system); module helpers like re.compile
                # are legitimate.
                base = func.value
                if (
                    func.attr in {"system", "popen"}
                    and isinstance(base, ast.Name)
                    and base.id in {"os", "subprocess"}
                ):
                    calls.add(f"{base.id}.{func.attr}")
    return imported, calls


def _relative_name(module: str) -> str:
    return module if module.startswith("resultseal") else module


def test_pure_modules_import_no_io() -> None:
    for name in sorted(PURE_MODULES):
        tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
        imported, _ = _imports_and_calls(tree)
        for module in imported:
            assert _relative_name(module) in PURE_ALLOWED_IMPORTS, (
                f"{name} imports {module}"
            )


def test_pure_modules_call_no_dangerous_builtin() -> None:
    for name in sorted(PURE_MODULES):
        tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
        _, calls = _imports_and_calls(tree)
        offenders = calls & FORBIDDEN_CALLS
        assert not offenders, f"{name} calls {sorted(offenders)}"


def test_no_module_imports_network_or_subprocess() -> None:
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported, _ = _imports_and_calls(tree)
        for module in imported:
            root = module.split(".")[0]
            assert root not in FORBIDDEN_IMPORT_ROOTS, (
                f"{path.name} imports {module}"
            )


def test_no_module_calls_dangerous_apis() -> None:
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        _, calls = _imports_and_calls(tree)
        offenders = calls & FORBIDDEN_CALLS
        assert not offenders, f"{path.name} calls {sorted(offenders)}"
