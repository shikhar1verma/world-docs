#!/usr/bin/env python3
"""
Verify — Claude Code docs output looks sane. Tune the expectations here if the
upstream docs legitimately shrink or rename sections.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import paths, verify as cverify                   # noqa: E402

NAME = Path(__file__).resolve().parent.name

MIN_PAGES = 100                        # currently ~156
REQUIRED_SECTIONS = ["getting-started"]
NAV_REFS = ["nav.json"]


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
