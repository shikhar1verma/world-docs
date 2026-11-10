#!/usr/bin/env python3
"""
Verify — OpenSpec docs output looks sane.

On top of the standard checks, every relative `*.md` link must resolve to a
mirrored file: refresh rewrites the upstream links to the local NN- layout,
and this is the detector for that rewrite silently going stale.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import paths, verify as cverify                   # noqa: E402

NAME = Path(__file__).resolve().parent.name

MIN_PAGES = 15                         # currently 20 (the pages openspec.dev/docs publishes)
REQUIRED_SECTIONS = ["start", "reference"]
NAV_REFS = ["docs.sync.config.mjs"]

_LINK_RE = re.compile(r"\]\(([^)]+)\)")             # same pattern refresh rewrites
_KEEP_LINK_RE = re.compile(r"^(?:https?:|mailto:|#|/)")
MAX_LINK_PROBLEMS = 10


def check_links(docs_dir) -> list:
    """Every relative `*.md` link in the mirrored pages must point at a real file."""
    root = Path(docs_dir)
    broken = []
    for page in cverify.iter_pages(root):
        for target in _LINK_RE.findall(page.read_text(encoding="utf-8", errors="replace")):
            path = target.partition("#")[0]
            if _KEEP_LINK_RE.match(target) or not path.lower().endswith(".md"):
                continue
            if not (page.parent / path).is_file():
                broken.append(f"{page.relative_to(root)}: broken link -> {target}")
    if len(broken) > MAX_LINK_PROBLEMS:
        extra = len(broken) - MAX_LINK_PROBLEMS
        broken = broken[:MAX_LINK_PROBLEMS] + [f"… and {extra} more broken links"]
    return broken


def verify() -> list:
    docs_dir = paths.docs_dir(NAME)
    problems = cverify.run(
        NAME, docs_dir,
        min_pages=MIN_PAGES,
        required_sections=REQUIRED_SECTIONS,
        nav_refs=NAV_REFS,
    )
    if docs_dir.is_dir():
        problems += check_links(docs_dir)
    return problems


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
