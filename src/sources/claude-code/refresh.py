#!/usr/bin/env python3
"""
Refresh — lay out fetched Claude Code pages under docs/claude-code/.

Reads ._temp/claude-code/nav.json and mirrors the live sidebar order as
NN- prefixed folders: tabs -> groups -> pages.

  docs/claude-code/
    01-getting-started/
      01-getting-started/
        01-overview.md
        ...
    nav.json          (ordering reference, no prefix)

Pages whose slug has its own path (e.g. agent-sdk/overview) keep only their leaf
name inside the group folder; the tab/group folders supply the hierarchy.
Assumes fetch() has already populated ._temp/ (the `wd` CLI runs fetch first).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import layout, paths                              # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
PAGES = TEMP / "pages"
NAV_JSON = TEMP / "nav.json"
DOCS = paths.docs_dir(NAME)
LANG = "en"


def _strip_lang(slug: str) -> str:
    return slug.split("/", 1)[1] if slug.startswith(LANG + "/") else slug


def collect_slugs(pages: list) -> list:
    out = []
    for p in pages:
        if isinstance(p, str):
            out.append(_strip_lang(p))
        elif isinstance(p, dict):
            out.extend(collect_slugs(p.get("pages", [])))
    return out


def _page_src(slug: str) -> Path:
    parts = slug.split("/")
    return PAGES.joinpath(*parts[:-1], parts[-1] + ".md")


def build_plan(nav: dict):
    """Ordered (dest_relpath, src_abspath) with NN- prefixes on tab/group/page."""
    plan = []
    for ti, tab in enumerate(nav["tabs"], start=1):
        tab_dir = f"{ti:02d}-{layout.slugify(tab['tab'])}"
        for gi, group in enumerate(tab.get("groups", []), start=1):
            group_dir = f"{gi:02d}-{layout.slugify(group['group'])}"
            for pi, slug in enumerate(collect_slugs(group.get("pages", [])), start=1):
                leaf = slug.split("/")[-1]
                dst = f"{tab_dir}/{group_dir}/{pi:02d}-{leaf}.md"
                plan.append((dst, _page_src(slug)))
    return plan


def refresh() -> dict:
    if not NAV_JSON.exists():
        raise FileNotFoundError(
            f"{NAV_JSON} not found — run `wd fetch {NAME}` first."
        )
    nav = json.loads(NAV_JSON.read_text(encoding="utf-8"))
    plan = build_plan(nav)
    print(f"  {len(nav['tabs'])} tabs, {len(plan)} pages to place")

    layout.clean_dir(DOCS)
    written, missing = layout.apply_plan(DOCS, plan)
    layout.copy_refs(TEMP, DOCS, ["nav.json"])

    print(f"Done — {written} pages written to {DOCS}")
    if missing:
        print(f"  {len(missing)} pages in nav had no downloaded .md (skipped)")
    return {"written": written, "missing": missing}


def main() -> None:
    refresh()


if __name__ == "__main__":
    main()
