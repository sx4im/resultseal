"""Safe-input tests: limits enforced pre-parse, unsafe YAML rejected, containment."""

from __future__ import annotations

import pytest

from resultseal.errors import LimitExceededError, ParseFailedError, UnsafeInputError
from resultseal.limits import Limits, walk_bounds
from resultseal.safeio import load_json, load_yaml, resolve_under_root

TIGHT = Limits(max_file_bytes=64, max_depth=8, max_nodes=32, max_string_chars=32)


def test_oversize_rejected_before_parse() -> None:
    big = b"a" * 65
    with pytest.raises(LimitExceededError):
        load_json(big, TIGHT)
    with pytest.raises(LimitExceededError):
        load_yaml(big, TIGHT)


def test_deep_nesting_rejected() -> None:
    doc = "[" * 40 + "]" * 40
    with pytest.raises(LimitExceededError):
        load_json(doc.encode(), TIGHT)


def test_json_nesting_beyond_interpreter_stack_is_a_limit_error() -> None:
    # Fits the default size limit but exceeds the C decoder's recursion
    # ceiling, so the parser itself fails before walk_bounds can run.
    doc = "[" * 60_000 + "]" * 60_000
    with pytest.raises(LimitExceededError):
        load_json(doc.encode(), Limits())


@pytest.mark.parametrize(
    "doc",
    ["[" * 30_000 + "]" * 30_000, "".join("  " * i + "-\n" for i in range(64))],
    ids=["flow", "block"],
)
def test_yaml_deep_nesting_rejected_before_composition(doc: str) -> None:
    with pytest.raises(LimitExceededError):
        load_yaml(doc.encode(), Limits())


@pytest.mark.parametrize(
    "doc", [b"a: !!int abc", b"a: !!float xyz", b"a: !!bool maybe", b"a: !!timestamp nope"]
)
def test_yaml_scalar_not_matching_its_tag_is_parse_failed(doc: bytes) -> None:
    with pytest.raises(ParseFailedError):
        load_yaml(doc, Limits())


def test_yaml_unhashable_key_rejected_as_unsafe() -> None:
    with pytest.raises(UnsafeInputError):
        load_yaml(b"? [a, b]\n: 1\n", Limits())


def test_long_string_rejected() -> None:
    with pytest.raises(LimitExceededError):
        load_json(('{"s": "' + "x" * 40 + '"}').encode(), TIGHT)


def test_node_count_rejected() -> None:
    doc = "[" * 10 + "0," * 30 + "]" * 10
    with pytest.raises(LimitExceededError):
        load_json(doc.encode(), TIGHT)


def test_benign_documents_load() -> None:
    assert load_json(b'{"a": [1, 2, {"b": null}]}', TIGHT) == {"a": [1, 2, {"b": None}]}
    assert load_yaml(b"a: 1\nb:\n  - x\n", TIGHT) == {"a": 1, "b": ["x"]}


def test_malformed_json_is_parse_failed() -> None:
    with pytest.raises(ParseFailedError):
        load_json(b"{broken", TIGHT)


def test_malformed_yaml_is_parse_failed() -> None:
    with pytest.raises(ParseFailedError):
        load_yaml(b"a: [unclosed\nb: }{", TIGHT)


def test_yaml_custom_tag_rejected_as_unsafe() -> None:
    payload = b'value: "!!python/object/apply:os.system [\'echo unsafe\']"'
    with pytest.raises(UnsafeInputError):
        load_yaml(payload, TIGHT)


def test_yaml_python_object_tag_rejected_as_unsafe() -> None:
    with pytest.raises(UnsafeInputError):
        load_yaml(b"!!python/object:os.system {}", TIGHT)


def test_yaml_anchor_alias_rejected() -> None:
    with pytest.raises(UnsafeInputError):
        load_yaml(b"a: &x [1]\nb: *x\n", TIGHT)


def test_billion_laughs_style_document_never_expands() -> None:
    bomb = (
        b"a0: &a0 [1,1,1,1,1,1,1,1,1]\n"
        b"a1: &a1 [*a0,*a0,*a0,*a0,*a0,*a0,*a0,*a0,*a0]\n"
    )
    with pytest.raises(UnsafeInputError):
        load_yaml(bomb, TIGHT)


def test_walk_bounds_direct() -> None:
    walk_bounds({"a": [1, 2]}, TIGHT)
    with pytest.raises(LimitExceededError):
        walk_bounds({"a" * 40: 1}, TIGHT)


def test_path_traversal_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    outside = tmp_path / ".." / "escape.json"
    with pytest.raises(UnsafeInputError):
        resolve_under_root(str(outside), tmp_path)
    inside = tmp_path / "sub" / ".." / "ok.json"
    assert resolve_under_root(str(inside), tmp_path) == (tmp_path / "ok.json").resolve()
