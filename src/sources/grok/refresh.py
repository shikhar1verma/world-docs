#!/usr/bin/env python3
"""
Refresh — lay out fetched Grok pages under docs/grok/.

Grok slugs are deeply hierarchical and their leaf names collide across sections,
so we do NOT flatten to the leaf. Top-level sections become NN- folders (numbered
by first appearance in the export); the rest of each slug path is mirrored
verbatim inside. A bare section-root slug (e.g. `overview`) lands as
NN-<section>/<section>.md.

  docs/grok/
    01-overview/overview.md
    04-developers/rest-api-reference/inference/chat.md
    llms.txt          (full export, no prefix)
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

REFERENCE_FILES = ["llms.txt"]


def build_plan(slugs):
    # Number top-level sections in first-appearance order.
    section_num = {}
    for slug in slugs:
        top = slug.split("/")[0]
        if top not in section_num:
            section_num[top] = len(section_num) + 1

    plan = []
    for slug in slugs:
        parts = slug.split("/")
        top = parts[0]
        rest = parts[1:] or [top]               # bare root -> NN-<top>/<top>.md
        sec_dir = f"{section_num[top]:02d}-{top}"
        dst = "/".join([sec_dir, *rest]) + ".md"
        src = PAGES.joinpath(*parts[:-1], parts[-1] + ".md")
        plan.append((dst, src))
    return plan


def refresh() -> dict:
    if not LLMS_TXT.exists():
        raise FileNotFoundError(f"{LLMS_TXT} not found — run `wd fetch {NAME}` first.")
    slugs = llms_txt.marker_order(LLMS_TXT.read_text(encoding="utf-8"))
    n_sections = len({s.split("/")[0] for s in slugs})
    plan = build_plan(slugs)
    print(f"  {n_sections} sections, {len(plan)} pages to place")

    layout.clean_dir(DOCS)
    written, missing = layout.apply_plan(DOCS, plan)
    layout.copy_refs(TEMP, DOCS, REFERENCE_FILES)

    print(f"Done — {written} pages written to {DOCS}")
    if missing:
        print(f"  {len(missing)} pages in export had no split .md (skipped)")
    return {"written": written, "missing": missing}


def main() -> None:
    refresh()


if __name__ == "__main__":
    main()
