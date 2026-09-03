"""ResultSeal command-line interface.

Commands and stable exit codes (CLI_CONTRACT.md):

- ``resultseal version``                                  -> always 0
- ``resultseal validate PATH``                            -> 0 valid / 2 invalid / 3 unsafe
- ``resultseal check RESPONSE --contract C``              -> 0 sealed / 1 blocked-or-unknown /
                                                            2 invalid invocation / 3 unsafe
- ``resultseal replay FIXTURE [FIXTURE ...]``             -> 0 expectations met / 1 mismatch /
                                                            2 invalid fixture / 3 unsafe

Errors print as ``resultseal: CODE: message`` on stderr and are never
swallowed. The CLI accepts data only — no expressions, URLs, imports, or
shell fragments. Wall-clock time is consulted only here (for the injected
reference clock); reports never carry it.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from resultseal import __version__
from resultseal.contracts import load_contract_file
from resultseal.errors import (
    InvalidArgumentError,
    ParseFailedError,
    ResultSealError,
    SchemaInvalidError,
)
from resultseal.fixtures import expectation_matches, load_fixture_file
from resultseal.limits import Limits
from resultseal.models import Contract, Decision, JsonValue
from resultseal.normalize import Normalization, infer_kind, normalize
from resultseal.report import (
    build_record,
    redact_record,
    render_json,
    render_markdown,
    with_fingerprint,
)
from resultseal.rules import Evaluation, ReferenceClock, evaluate, format_clock
from resultseal.safeio import load_json, load_yaml

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_INVALID = 2
EXIT_UNSAFE = 3

_LIMITS = Limits()

_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _color_verdict(verdict: str) -> str:
    """Highlight verdicts only on an interactive, color-enabled stdout."""
    if "NO_COLOR" in os.environ or not sys.stdout.isatty():
        return verdict
    color = _GREEN if verdict in {"sealed", "MATCH"} else _RED
    return f"{color}{verdict}{_RESET}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resultseal",
        description="Deterministic observation-integrity checks for tool results.",
    )
    parser.add_argument("--version", action="version", version=f"resultseal {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    version_parser = subparsers.add_parser("version", help="Print the package version.")
    version_parser.set_defaults(func=_run_version)

    validate_parser = subparsers.add_parser(
        "validate", help="Validate contract or fixture documents."
    )
    validate_parser.add_argument("path", type=str)
    validate_parser.set_defaults(func=_run_validate)

    check_parser = subparsers.add_parser(
        "check", help="Normalize and evaluate one response against a contract."
    )
    check_parser.add_argument("response", type=str)
    check_parser.add_argument("--contract", required=True, type=str)
    _add_common_flags(check_parser, default_format="json")
    check_parser.set_defaults(func=_run_check)

    replay_parser = subparsers.add_parser(
        "replay", help="Replay deterministic fixture(s) against their expectations."
    )
    replay_parser.add_argument("fixtures", nargs="+", type=str)
    _add_common_flags(replay_parser, default_format="md")
    replay_parser.set_defaults(func=_run_replay)

    return parser


def _add_common_flags(parser: argparse.ArgumentParser, *, default_format: str) -> None:
    parser.add_argument("--format", choices=("json", "md"), default=default_format)
    parser.add_argument("--now", type=str, default=None, help="ISO-8601 reference clock.")
    parser.add_argument("--redact", action="append", default=[], metavar="FIELD")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_usage(sys.stderr)
        return EXIT_INVALID
    try:
        return int(args.func(args))
    except ResultSealError as exc:
        print(f"resultseal: {exc}", file=sys.stderr)
        return exc.exit_code


def _run_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return EXIT_OK


def _parse_now(raw: str | None) -> ReferenceClock:
    if raw is None:
        return ReferenceClock(now=datetime.now(UTC))
    text = raw.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidArgumentError(
            "--now must be an ISO-8601 timestamp", detail=raw
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return ReferenceClock(now=parsed)


def _read_document(path_text: str) -> tuple[Path, object]:
    path = Path(path_text)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ParseFailedError("file could not be read", detail=str(exc)[:120]) from exc
    if path.suffix.lower() in (".yaml", ".yml"):
        return path, load_yaml(data, _LIMITS)
    return path, load_json(data, _LIMITS)


def _validate_document(path: Path, doc: object) -> str:
    if not isinstance(doc, dict):
        raise SchemaInvalidError("document must be an object")
    if "fixture_version" in doc:
        load_fixture_file(path, _LIMITS)
        return "fixture"
    if "schema_version" in doc and "claim_type" in doc:
        load_contract_file(path, _LIMITS)
        return "contract"
    raise SchemaInvalidError(
        "unrecognized document", detail="expected a fixture or contract object"
    )


def _run_validate(args: argparse.Namespace) -> int:
    path, doc = _read_document(args.path)
    kind = _validate_document(path, doc)
    print(f"{args.path}: valid ({kind})")
    return EXIT_OK


def _load_contract(path_text: str) -> Contract:
    return load_contract_file(Path(path_text), _LIMITS)


def _normalize_and_evaluate(
    raw: dict[str, JsonValue], contract: Contract, clock: ReferenceClock
) -> tuple[Normalization, Evaluation]:
    if "kind" not in raw:
        raw = {"kind": infer_kind(raw), **raw}
    normalization: Normalization = normalize(raw, clock)
    evaluation = evaluate(normalization.envelope, normalization.payload, contract, clock)
    return normalization, evaluation


def _stamped_record(
    evaluation: Evaluation,
    normalization: Normalization,
    contract: Contract,
    redactions: list[str],
) -> dict[str, JsonValue]:
    """Build, redact, then fingerprint — the one record pipeline for emitters."""
    record = build_record(
        evaluation, normalization.envelope, contract, resultseal_version=__version__
    )
    if redactions:
        record = redact_record(record, redactions)
    return with_fingerprint(record)


def _emit(
    fmt: str,
    normalization: Normalization,
    evaluation: Evaluation,
    contract: Contract,
    clock: ReferenceClock,
    redactions: list[str],
) -> None:
    stamped = _stamped_record(evaluation, normalization, contract, redactions)
    if fmt == "json":
        print(render_json(stamped))
        return
    env = normalization.envelope
    # Echo identity through the (possibly redacted) record so secrets do
    # not leak into the human-readable sections.
    report = render_markdown(
        stamped,
        input_summary=(
            f"tool={env.tool_name} source={stamped['source_ref']} "
            f"target={env.target_ref} evidence={stamped['evidence_refs']}"
        ),
        normalized_state=(
            f"transport={env.transport_state.value} "
            f"observed={env.truth_state.value}"
        ),
        clock_note=format_clock(clock.now),
    )
    verdict = evaluation.decision.value
    print(report.replace(f"\n{verdict} (", f"\n{_color_verdict(verdict)} (", 1))


def _run_check(args: argparse.Namespace) -> int:
    _, doc = _read_document(args.response)
    if not isinstance(doc, dict):
        raise SchemaInvalidError("response document must be an object")
    contract = _load_contract(args.contract)
    clock = _parse_now(args.now)
    normalization, evaluation = _normalize_and_evaluate(doc, contract, clock)
    _emit(args.format, normalization, evaluation, contract, clock, args.redact)
    return EXIT_OK if evaluation.decision is Decision.SEALED else EXIT_BLOCKED


def _replay_one(
    path_text: str, fmt: str, clock: ReferenceClock, redactions: list[str]
) -> bool:
    """Return True when the fixture's expectation matched."""
    bundle = load_fixture_file(Path(path_text), _LIMITS)
    contract = bundle.contract
    if contract is None:
        if bundle.expected.decision_literal != "rejected":
            raise SchemaInvalidError(
                "fixture has no embedded contract and cannot be replayed",
                detail=path_text,
            )
        # Rejected-expectation fixture: input preparation itself must refuse
        # (e.g. a nested YAML payload carrying an unsafe tag). Reaching this
        # point means it did not.
        normalize(dict(bundle.raw_input), clock)
        raise SchemaInvalidError(
            "fixture expected rejection but its input prepared cleanly",
            detail=path_text,
        )
    raw = dict(bundle.raw_input)
    normalization, evaluation = _normalize_and_evaluate(raw, contract, clock)

    expectation = bundle.expected
    matched = expectation_matches(expectation, evaluation)

    if fmt == "json":
        print(
            render_json(_stamped_record(evaluation, normalization, contract, redactions))
        )
    else:
        verdict = "MATCH" if matched else "MISMATCH"
        print(
            f"{_color_verdict(verdict)}: {bundle.name} -> "
            f"{evaluation.truth_state.value}/{evaluation.decision.value}"
        )
        if not matched:
            print(
                f"  expected: {expectation.truth_state.value if expectation.truth_state else '*'}"
                f"/{expectation.decision_literal}"
                f" codes={list(expectation.reason_codes)}"
            )
            print(
                f"  actual:   {evaluation.truth_state.value}"
                f"/{evaluation.decision.value}"
                f" codes={list(evaluation.reason_codes)}"
            )
    return matched


def _run_replay(args: argparse.Namespace) -> int:
    clock = _parse_now(args.now)
    all_matched = True
    for fixture_path in args.fixtures:
        if not _replay_one(fixture_path, args.format, clock, args.redact):
            all_matched = False
    return EXIT_OK if all_matched else EXIT_BLOCKED


if __name__ == "__main__":
    sys.exit(main())

