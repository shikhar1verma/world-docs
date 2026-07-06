#!/usr/bin/env python3
"""
Refresh — lay out fetched Codex pages under docs/codex/.

Sections become NN- folders (in llms.txt order); pages are flattened to their
leaf name inside, NN- prefixed:

  docs/codex/
    06-cli/
      01-cli.md
      02-features.md
      03-reference.md
    llms.txt / llms-full.txt / codex-manual.md   (references, no prefix)

Pages whose slug has its own path (e.g. cli/reference) keep only the leaf name;
the section folder supplies the hierarchy.
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

MARKER = "/codex/"
SKIP_SECTIONS = {"documentation sets"}
REFERENCE_FILES = ["llms.txt", "llms-full.txt", "codex-manual.md"]


def _page_src(slug: str) -> Path:
    parts = slug.split("/")
    return PAGES.joinpath(*parts[:-1], parts[-1] + ".md")


def build_plan(sections):
    plan = []
    for si, (title, slugs) in enumerate(sections, start=1):
        sec_dir = f"{si:02d}-{layout.slugify(title)}"
        for pi, slug in enumerate(slugs, start=1):
            leaf = slug.split("/")[-1]
            plan.append((f"{sec_dir}/{pi:02d}-{leaf}.md", _page_src(slug)))
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
