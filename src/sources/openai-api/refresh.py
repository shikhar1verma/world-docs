#!/usr/bin/env python3
"""
Refresh — lay out fetched OpenAI API pages under docs/openai-api/.

The index has just two content sections (Docs, Reference); the real hierarchy is
encoded *inside* each slug, up to ~11 levels deep, and leaf names collide heavily
(dozens of create/list/delete). So we do NOT flatten to the leaf — we number the
two section folders and mirror the full slug path verbatim inside (dropping the
redundant leading docs/|reference/ segment the NN-<section> folder already carries).

  docs/openai-api/
    01-docs/guides/function-calling.md
    02-reference/resources/audio/subresources/speech/methods/create.md
    llms.txt / llms-full.txt   (references, no prefix)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import layout, llms_txt, paths                    # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
PAGES = TEMP / "pages"
LLMS_TXT = TEMP / "llms.txt"
DOCS = paths.docs_dir(NAME)

MARKER = "/api/"
SKIP_SECTIONS = {"documentation sets"}
REFERENCE_FILES = ["llms.txt", "llms-full.txt"]


def _page_src(slug: str) -> Path:
    parts = slug.split("/")
    return PAGES.joinpath(*parts[:-1], parts[-1] + ".md")


def build_plan(sections):
    plan = []
    for si, (title, slugs) in enumerate(sections, start=1):
        sec_slug = layout.slugify(title)        # "docs", "reference"
        sec_dir = f"{si:02d}-{sec_slug}"
        for slug in slugs:
            parts = slug.split("/")
            if parts and parts[0] == sec_slug:  # drop redundant leading segment
                parts = parts[1:]
            if not parts:                        # slug was exactly the section root
                parts = [sec_slug]
            dst = "/".join([sec_dir, *parts]) + ".md"
            plan.append((dst, _page_src(slug)))
    return plan


def refresh() -> dict:
    if not LLMS_TXT.exists():
        raise FileNotFoundError(f"{LLMS_TXT} not found — run `wd fetch {NAME}` first.")
    sections = llms_txt.parse_sections(
        LLMS_TXT.read_text(encoding="utf-8"), MARKER, skip=SKIP_SECTIONS)
    plan = build_plan(sections)
    print(f"  {len(sections)} sections, {len(plan)} pages to place")

    layout.clean_dir(DOCS)
    written, missing = layout.apply_plan(DOCS, plan)
    layout.copy_refs(TEMP, DOCS, REFERENCE_FILES)

    print(f"Done — {written} pages written to {DOCS}")
    if missing:
        print(f"  {len(missing)} pages in llms.txt had no downloaded .md (skipped)")
    return {"written": written, "missing": missing}


def main() -> None:
    refresh()


if __name__ == "__main__":
    main()
