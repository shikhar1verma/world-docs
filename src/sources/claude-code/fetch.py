#!/usr/bin/env python3
"""
Fetch — Claude Code docs (code.claude.com) → ._temp/claude-code/.

Claude Code has no public docs repo, so this is the "clone" step done over HTTP:
  1. Download one rendered page (overview) and extract the full navigation tree
     embedded in its Next.js flight payload (navigation.languages[en]).
  2. Write that tree to ._temp/claude-code/nav.json (our docs.json equivalent).
  3. Download every page's Markdown by appending `.md` to its slug
     (https://code.claude.com/docs/en/<slug>.md), in parallel.

FRAGILE POINT: extract_navigation() locates the nav by scanning for the escaped
`\\"navigation\\":` key in the page HTML and brace-matching the object. If
code.claude.com changes how it embeds navigation, patch that function (see
this folder's README.md).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import http, layout, paths                        # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
PAGES = TEMP / "pages"
NAV_JSON = TEMP / "nav.json"

BASE = "https://code.claude.com/docs"
SEED_PAGE = f"{BASE}/en/overview"       # any page embeds the full nav
LANG = "en"
USER_AGENT = "world-docs-claude-code-fetch/1.0"


# ---------------------------------------------------------------------------
# Navigation extraction (source-specific, fragile)
# ---------------------------------------------------------------------------

def extract_navigation(html: str) -> dict:
    """
    Pull the `navigation` object out of the Next.js flight payload embedded in
    the page HTML. The payload is a JS string, so JSON quotes appear escaped as
    \\". We scan a balanced-brace object starting at "navigation": then run it
    through unicode_escape to recover real JSON.
    """
    key = '\\"navigation\\":'
    i = html.find(key)
    if i == -1:
        raise RuntimeError("navigation block not found in page HTML")
    start = html.find("{", i)

    depth = 0
    in_str = False
    j = start
    out = []
    while j < len(html):
        if html[j:j + 2] == '\\"':       # escaped quote = string boundary
            in_str = not in_str
            out.append('\\"')
            j += 2
            continue
        c = html[j]
        out.append(c)
        if not in_str:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
        j += 1
    else:
        raise RuntimeError("unterminated navigation object")

    escaped = "".join(out)
    unescaped = escaped.encode("utf-8").decode("unicode_escape")
    return json.loads(unescaped)


def english_tabs(navigation: dict) -> list:
    langs = navigation.get("languages", [])
    en = next((l for l in langs if l.get("language") == LANG), None)
    if en is None and langs:
        en = langs[0]
    if en is None:
        raise RuntimeError("no languages in navigation")
    return en.get("tabs", [])


def _strip_lang(slug: str) -> str:
    return slug[len(LANG) + 1:] if slug.startswith(LANG + "/") else slug


def collect_slugs(pages: list) -> list:
    """Recursively flatten page slugs (strip the `en/` language prefix)."""
    out = []
    for p in pages:
        if isinstance(p, str):
            out.append(_strip_lang(p))
        elif isinstance(p, dict):
            out.extend(collect_slugs(p.get("pages", [])))
    return out


def all_slugs(tabs: list) -> list:
    out, seen = [], set()
    for tab in tabs:
        for group in tab.get("groups", []):
            for slug in collect_slugs(group.get("pages", [])):
                if slug not in seen:
                    seen.add(slug)
                    out.append(slug)
    return out


def _page_dest(slug: str) -> Path:
    parts = slug.split("/")
    return PAGES.joinpath(*parts[:-1], parts[-1] + ".md")


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch() -> None:
    print(f"Fetching seed page for navigation: {SEED_PAGE}")
    html = http.get(SEED_PAGE, user_agent=USER_AGENT)
    tabs = english_tabs(extract_navigation(html))
    slugs = all_slugs(tabs)
    print(f"  {len(tabs)} tabs, {len(slugs)} pages in navigation")

    layout.clean_dir(PAGES)                     # also (re)creates TEMP
    NAV_JSON.write_text(
        json.dumps({"language": LANG, "tabs": tabs}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  wrote {NAV_JSON}")

    print(f"Downloading {len(slugs)} pages (.md) …")
    ok, failures = http.download_slugs(
        slugs,
        url_for=lambda s: f"{BASE}/{LANG}/{s}.md",
        dest_for=_page_dest,
        user_agent=USER_AGENT,
    )
    print(f"Done — {ok}/{len(slugs)} pages downloaded to {PAGES}")
    if failures:
        print(f"  {len(failures)} pages failed (verify will flag large gaps)")


def main() -> None:
    fetch()


if __name__ == "__main__":
    main()
