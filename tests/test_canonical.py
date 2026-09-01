"""Phase 2 canonicalization tests: stable bytes, hashes, fingerprints."""

from __future__ import annotations

import hashlib
import re

import pytest

from resultseal.canonical import canonical_json, content_hash, decision_fingerprint
from resultseal.errors import SchemaInvalidError

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def test_key_order_independence() -> None:
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})


def test_nested_key_order_independence() -> None:
    left = {"outer": {"x": 1, "y": 2}, "list": [{"p": 1, "q": 2}]}
    right = {"list": [{"q": 2, "p": 1}], "outer": {"y": 2, "x": 1}}
    assert canonical_json(left) == canonical_json(right)


def test_stable_across_runs() -> None:
    payload = {"k": [1, 2, {"z": "é", "a": None}], "n": 3}
    assert canonical_json(payload) == canonical_json(payload)


def test_unicode_encoded_as_utf8() -> None:
    assert "é".encode() in canonical_json({"u": "é"})


def test_no_insignificant_whitespace() -> None:
    assert canonical_json({"a": 1, "b": [1, 2]}) == b'{"a":1,"b":[1,2]}'


def test_nan_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        canonical_json({"a": float("nan")})


def test_non_string_keys_rejected() -> None:
    with pytest.raises(SchemaInvalidError):
        canonical_json({1: "a"})  # type: ignore[dict-item]


def test_content_hash_format_and_stability() -> None:
    first = content_hash({"a": 1})
    assert _SHA256_RE.fullmatch(first)
    assert first == content_hash({"a": 1})
    assert first == "sha256:" + hashlib.sha256(b'{"a":1}').hexdigest()


def test_content_hash_sensitive_to_content() -> None:
    assert content_hash({"a": 1}) != content_hash({"a": 2})


def test_fingerprint_excludes_itself() -> None:
    record = {"decision": "sealed", "truth_state": "sealed"}
    with_self = dict(record, deterministic_fingerprint="sha256:" + "f" * 64)
    assert decision_fingerprint(with_self) == decision_fingerprint(record)
    assert _SHA256_RE.fullmatch(decision_fingerprint(record))


def test_negative_zero_canonical_hash_identity() -> None:
    hash_pos = content_hash({"val": 0.0})
    hash_neg = content_hash({"val": -0.0})
    assert canonical_json({"val": -0.0}) == b'{"val":0.0}'
    assert hash_neg == hash_pos
