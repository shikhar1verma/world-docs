#!/usr/bin/env python3
"""Verify — Codex docs output looks sane."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import paths, verify as cverify                   # noqa: E402

NAME = Path(__file__).resolve().parent.name

MIN_PAGES = 60                         # currently ~95
REQUIRED_SECTIONS = []                 # sections are dynamic (llms.txt headings)
NAV_REFS = ["llms.txt"]


def verify() -> list:
    return cverify.run(
        NAME, paths.docs_dir(NAME),
        min_pages=MIN_PAGES,
        required_sections=REQUIRED_SECTIONS,
        nav_refs=NAV_REFS,
    )


def main() -> None:
    problems = verify()
    if problems:
        print(f"FAIL {NAME}:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"PASS {NAME} ({cverify.count_pages(paths.docs_dir(NAME))} pages)")


if __name__ == "__main__":
    main()
