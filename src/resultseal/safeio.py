"""Safe loading of untrusted JSON/YAML documents.

YAML is loaded only through the safe loader. Before parsing, the event
stream is scanned: any anchor, alias, or non-YAML-2002 tag is rejected as
``UNSAFE_INPUT`` — this structurally rules out alias-bomb expansion and
object construction. The same scan bounds collection nesting, so deeply
nested input is refused before the recursive composer can exhaust the
interpreter stack. Syntax errors are ``PARSE_FAILED``; size is checked
before parse; depth/nodes/strings immediately after.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import yaml

from resultseal.errors import (
    LimitExceededError,
    ParseFailedError,
    PathEscapeError,
    UnsafeInputError,
)
from resultseal.limits import Limits, check_size, walk_bounds
from resultseal.models import JsonValue

_YAML_TAG_PREFIX = "tag:yaml.org,2002:"


def load_json(data: bytes, limits: Limits) -> JsonValue:
    check_size(len(data), limits)
    try:
        # json.loads returns Any by contract; walk_bounds validates shape.
        doc = cast(JsonValue, json.loads(data))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParseFailedError("input is not valid JSON", detail=str(exc)[:120]) from exc
    except RecursionError as exc:
        raise LimitExceededError(f"nesting exceeds {limits.max_depth} levels") from exc
    walk_bounds(doc, limits)
    return doc


def load_yaml(data: bytes, limits: Limits) -> JsonValue:
    check_size(len(data), limits)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ParseFailedError("input is not valid UTF-8", detail=str(exc)[:120]) from exc
    _scan_events(text, limits)
    try:
        doc: object = yaml.safe_load(text)
    except yaml.constructor.ConstructorError as exc:
        raise UnsafeInputError(
            "YAML document uses an unsupported construct",
            detail=str(exc.problem)[:120],
        ) from exc
    except yaml.YAMLError as exc:
        raise ParseFailedError("input is not valid YAML", detail=str(exc)[:120]) from exc
    except (ValueError, LookupError, AttributeError) as exc:
        # PyYAML's safe constructor raises bare builtins for explicitly tagged
        # scalars that do not parse under their tag (``!!int abc``,
        # ``!!bool maybe``, ``!!timestamp nope``).
        raise ParseFailedError(
            "YAML scalar does not match its tag", detail=str(exc)[:120]
        ) from exc
    if doc is not None and not isinstance(doc, (str, int, float, bool, dict, list)):
        raise LimitExceededError("document root must be a mapping, sequence, or scalar")
    walk_bounds(doc, limits)
    return doc


def resolve_under_root(path_text: str, root: Path) -> Path:
    """Resolve *path_text* and require it to stay inside *root*."""
    root_resolved = root.resolve()
    candidate = Path(path_text)
    resolved = candidate.resolve() if candidate.is_absolute() else (
        root_resolved / candidate
    ).resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise PathEscapeError(
            "path escapes its allowed root",
            detail=f"{path_text!r} resolves outside {str(root_resolved)!r}",
        )
    return resolved


# Only these yaml.org,2002 tags may appear. Everything else — including the
# `!!` shorthand of anything outside this set, e.g. python/object — is unsafe.
_ALLOWED_YAML_TAGS = frozenset(
    {
        "tag:yaml.org,2002:str",
        "tag:yaml.org,2002:int",
        "tag:yaml.org,2002:float",
        "tag:yaml.org,2002:bool",
        "tag:yaml.org,2002:null",
        "tag:yaml.org,2002:seq",
        "tag:yaml.org,2002:map",
        "tag:yaml.org,2002:timestamp",
    }
)


def _scan_events(text: str, limits: Limits) -> None:
    # Events are consumed lazily: PyYAML's scanner is quadratic in flow
    # nesting depth, so the depth bound must trip before the whole document
    # is tokenized.
    depth = 0
    try:
        for event in yaml.parse(text):
            if isinstance(event, yaml.CollectionStartEvent):
                depth += 1
                if depth > limits.max_depth:
                    raise LimitExceededError(f"nesting exceeds {limits.max_depth} levels")
            elif isinstance(event, yaml.CollectionEndEvent):
                depth -= 1
            anchor = getattr(event, "anchor", None)
            if anchor:
                raise UnsafeInputError(
                    "YAML anchors and aliases are not accepted", detail=str(anchor)[:80]
                )
            tag = getattr(event, "tag", None)
            if tag is None:
                continue
            tag_text = str(tag)
            if tag_text.startswith(_YAML_TAG_PREFIX) and tag_text in _ALLOWED_YAML_TAGS:
                continue
            raise UnsafeInputError("custom YAML tags are not accepted", detail=tag_text[:80])
    except yaml.YAMLError as exc:
        raise ParseFailedError("input is not valid YAML", detail=str(exc)[:120]) from exc
