#!/usr/bin/env python3
"""
Fetch — OpenAI Codex docs (developers.openai.com/codex) → ._temp/codex/.

Codex docs are not in a public git repo, so this is the HTTP "clone" step:
  1. Download the navigation index `codex/llms.txt` (Markdown: `## Section`
     headings + `- [title](url)` bullets pointing at per-page `.md` twins).
  2. Download every page's Markdown twin at `/codex/<slug>.md`, in parallel.
  3. Download the whole-file "Documentation sets" references
     (llms-full.txt, codex-manual.md) to the temp root.

FRAGILE POINT: page URLs are identified by the `/codex/` path marker and the
`## Section` / `- [t](url)` line shapes. If either changes, patch MARKER or the
parser in common/llms_txt.py (see this folder's README.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import http, layout, llms_txt, paths              # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
PAGES = TEMP / "pages"
LLMS_TXT = TEMP / "llms.txt"

BASE = "https://developers.openai.com/codex"
LLMS_URL = f"{BASE}/llms.txt"
MARKER = "/codex/"
SKIP_SECTIONS = {"documentation sets"}
DOC_SET_FILES = ["llms-full.txt", "codex-manual.md"]
USER_AGENT = "world-docs-codex-fetch/1.0"


def _page_dest(slug: str) -> Path:
    parts = slug.split("/")
    return PAGES.joinpath(*parts[:-1], parts[-1] + ".md")


def fetch() -> None:
    print(f"Fetching navigation index: {LLMS_URL}")
    llms = http.get(LLMS_URL, user_agent=USER_AGENT)

    layout.clean_dir(PAGES)                     # also (re)creates TEMP
    LLMS_TXT.write_text(llms, encoding="utf-8")

    sections = llms_txt.parse_sections(llms, MARKER, skip=SKIP_SECTIONS)
    slugs = [s for _, slugs in sections for s in slugs]
    print(f"  {len(sections)} sections, {len(slugs)} content pages")

    print(f"Downloading {len(slugs)} pages (.md) …")
    ok, failures = http.download_slugs(
        slugs,
        url_for=lambda s: f"{BASE}/{s}.md",
        dest_for=_page_dest,
        user_agent=USER_AGENT,
    )

    for name in DOC_SET_FILES:
        try:
            (TEMP / name).write_text(
                http.get(f"{BASE}/{name}", user_agent=USER_AGENT), encoding="utf-8")
            print(f"  ✓ {name}")
        except Exception as e:                   # noqa: BLE001
            print(f"  ✗ {name}: {e}")

    print(f"Done — {ok}/{len(slugs)} pages downloaded to {PAGES}")
    if failures:
        print(f"  {len(failures)} pages failed (verify will flag large gaps)")


def main() -> None:
    fetch()


if __name__ == "__main__":
    main()
