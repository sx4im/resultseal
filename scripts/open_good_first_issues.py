#!/usr/bin/env python3
"""Open the drafted issues in docs/community/good-first-issues/ with the gh CLI.

Dry run by default; pass --create to open them. Titles that already exist as
an issue (open or closed) are skipped, so the script is safe to rerun.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DRAFTS = Path(__file__).resolve().parent.parent / "docs" / "community" / "good-first-issues"


def parse(path: Path) -> tuple[str, list[str], str]:
    text = path.read_text(encoding="utf-8")
    _, front, body = text.split("---\n", 2)
    fields = dict(line.split(": ", 1) for line in front.strip().splitlines())
    title = json.loads(fields["title"]) if fields["title"].startswith('"') else fields["title"]
    labels = [label.strip() for label in fields["labels"].split(",")]
    return title, labels, body.lstrip()


def existing_titles(repo: str) -> set[str]:
    out = subprocess.run(
        ["gh", "issue", "list", "-R", repo, "--state", "all", "--limit", "500",
         "--json", "title"],
        check=True, capture_output=True, text=True,
    ).stdout
    return {issue["title"] for issue in json.loads(out)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="sx4im/resultseal")
    parser.add_argument("--create", action="store_true", help="Open the issues.")
    args = parser.parse_args()

    seen = existing_titles(args.repo)
    for path in sorted(DRAFTS.glob("*.md")):
        title, labels, body = parse(path)
        if title in seen:
            print(f"skip (exists): {title}")
            continue
        if not args.create:
            print(f"would open: {title}  [{', '.join(labels)}]")
            continue
        command = ["gh", "issue", "create", "-R", args.repo, "--title", title, "--body", body]
        for label in labels:
            command += ["--label", label]
        url = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        print(f"opened: {url.strip()}  {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
