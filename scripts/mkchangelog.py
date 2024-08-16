#!/usr/bin/env python
# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections
import logging
import re
import subprocess
import sys

import click

from capellambse import helpers

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

CONCOM = re.compile(
    r"^(?P<type>\w+)(?:\((?P<scope>[A-Za-z0-9_-]+)\))?(?P<breaking>\!)?: (?P<subject>.*)$"
)
LOGGER = logging.getLogger(__name__)
MAILUSER = re.compile(
    r"^(?:\d+\+)?(?P<user>[^@]+)@users\.noreply\.github\.com$"
)

HEADINGS: tuple[tuple[str, str | None], ...] = (
    ("BAD", "Commits with malformed subject lines"),
    ("revert", "Reverted earlier changes"),
    ("feat", "New features"),
    ("perf", "Performance improvements"),
    ("fix", "Bug fixes"),
    ("docs", "Documentation changes"),
    ("build", "Build system changes"),
    ("ci", "CI/CD changes"),
    ("test", "Unit test changes"),
    ("refactor", "Code refactorings"),
    ("merge", None),
    ("chore", None),
)


@click.command()
@click.argument("since", required=True)
@click.argument("until", default="HEAD")
def _main(since: str, until: str) -> None:
    """Generate the changelog between the given commit-ish.

    SINCE is exclusive, UNTIL is inclusive.
    """
    try:
        with open("authors.toml", "rb") as f:
            authormap: dict[str, str] = tomllib.load(f)
    except FileNotFoundError:
        LOGGER.warning("authors.toml not found, cannot map authors to users")
        authormap = {}

    format = "format:%s%x00%aE%x00%H"
    all_commits = subprocess.check_output(
        ["git", "log", "-z", f"--format={format}", f"{since}..{until}"],
        encoding="utf-8",
    )
    commits: dict[str, list[str]] = collections.defaultdict(list)
    breaking_changes: list[str] = []

    unknown_authors: set[str] = set()
    for msg, author, hash in helpers.ntuples(3, all_commits.split("\0")):
        if author_match := MAILUSER.search(author):
            author = "@" + author_match.group("user")
        else:
            try:
                author = authormap[author]
            except KeyError:
                if author not in unknown_authors:
                    print(f"Unknown author email: {author}")
                    unknown_authors.add(author)

        if not (msg_match := CONCOM.search(msg)):
            LOGGER.warning("Bad commit subject: %s %s", hash, msg)
            msg = msg[0].upper() + msg[1:]
            commits["BAD"].append(f"{msg} *by {author}* ({hash})")
            continue

        ctype, scope, breaking, subject = msg_match.group(
            "type", "scope", "breaking", "subject"
        )
        scope = f"**{scope}**: " if scope else ""
        subject = subject[0].upper() + subject[1:]
        commits[ctype].append(f"{scope}{subject} *by {author}* ({hash})")
        if breaking:
            breaking_changes.append(f"{scope}{subject}")

    try:
        with open("notable-changes.md", encoding="locale") as f:
            custom_changes = f.read().strip()
    except FileNotFoundError:
        custom_changes = ""
    except Exception as err:
        errtext = f" {type(err).__name__}: {err}"
        custom_changes = f"***Cannot read notable-changes.md:*** {errtext}"

    if breaking_changes:
        print("# Breaking changes", end="\n\n")
        for msg in breaking_changes:
            print(f"- {msg}")
        print()

        print("# Other notable changes", end="\n\n")
    else:
        print("# Notable changes", end="\n\n")
    if custom_changes:
        print(custom_changes.strip(), end="\n\n")
    print("# Full changelog", end="\n\n")

    for ctype, heading in HEADINGS:
        if ctype not in commits:
            continue

        if heading is None:
            del commits[ctype]
            continue

        print(f"## {heading}", end="\n\n")
        for msg in commits.pop(ctype):
            print(f"- {msg}")
        print()

    for ctype, msgs in commits.items():
        print(f"## {ctype.capitalize()}", end="\n\n")
        for msg in msgs:
            print(f"- {msg}")
        print()


if __name__ == "__main__":
    _main()
