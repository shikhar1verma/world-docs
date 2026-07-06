#!/usr/bin/env python3
"""
Fetch — OpenAI API docs (developers.openai.com/api) → ._temp/openai-api/.

Same HTTP "clone" shape as Codex, against the /api/ base: download the
`api/llms.txt` index, then every page's `.md` twin at `/api/<slug>.md` in
parallel, plus the combined `llms-full.txt` export. Slugs here are deep
(e.g. reference/resources/audio/subresources/speech/methods/create) and their
leaf names collide heavily — the refresh step keeps the full path (see refresh.py).

FRAGILE POINT: the `/api/` path marker and llms.txt line shapes (parser in
common/llms_txt.py). See this folder's README.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import http, layout, llms_txt, paths              # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
PAGES = TEMP / "pages"
LLMS_TXT = TEMP / "llms.txt"

BASE = "https://developers.openai.com/api"
LLMS_URL = f"{BASE}/llms.txt"
MARKER = "/api/"
SKIP_SECTIONS = {"documentation sets"}
DOC_SET_FILES = ["llms-full.txt"]
USER_AGENT = "world-docs-openai-api-fetch/1.0"


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
