#!/usr/bin/env python3
"""
Fetch — Grok / xAI docs (docs.x.ai) → ._temp/grok/.

Unlike the OpenAI/Codex indexes, Grok's `llms.txt` is a single ~1.2 MB
concatenated export: every page's Markdown inlined, delimited by `===/<slug>===`
marker lines. So the whole corpus arrives in one download; we split it locally
(byte-for-byte consistent with the published export, no per-page requests).

FRAGILE POINT: the `===/<slug>===` marker format. If it changes, patch
MARKER_RE in common/llms_txt.py (see this folder's README.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import http, layout, llms_txt, paths              # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
PAGES = TEMP / "pages"
LLMS_TXT = TEMP / "llms.txt"

BASE = "https://docs.x.ai"
LLMS_URL = f"{BASE}/llms.txt"
USER_AGENT = "world-docs-grok-fetch/1.0"
TIMEOUT = 60                            # the single file is large


def fetch() -> None:
    print(f"Fetching docs export: {LLMS_URL}")
    llms = http.get(LLMS_URL, user_agent=USER_AGENT, timeout=TIMEOUT)

    layout.clean_dir(PAGES)                     # also (re)creates TEMP
    LLMS_TXT.write_text(llms, encoding="utf-8")
    print(f"  wrote {LLMS_TXT} ({len(llms)} bytes)")

    pages = llms_txt.split_markers(llms)
    print(f"  {len(pages)} pages found in export")
    for slug, body in pages:
        parts = slug.split("/")
        dst = PAGES.joinpath(*parts[:-1], parts[-1] + ".md")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(body + "\n", encoding="utf-8")

    print(f"Done — {len(pages)} pages written to {PAGES}")
    if not pages:
        raise RuntimeError("no pages parsed — marker format may have changed")


def main() -> None:
    fetch()


if __name__ == "__main__":
    main()
