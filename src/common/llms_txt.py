"""
Parsers for the navigation/index formats the direct-fetch sources publish.

Two shapes appear in the wild:

1. **Index style** (OpenAI API, Codex): ``llms.txt`` is Markdown — a few
   ``## Section`` headings, each followed by ``- [title](url): desc`` bullets
   where every ``url`` points at a per-page ``.md`` twin. ``parse_sections``
   turns that into an ordered ``[(section_title, [slug, ...])]``.

2. **Concatenated style** (Grok): ``llms.txt`` is one big export with every
   page inlined, delimited by ``===/<slug>===`` marker lines. ``split_markers``
   yields ``[(slug, body)]`` and ``marker_order`` yields just the slug order.

Both are pure text transforms — no HTTP, no filesystem.
"""

import re

_SECTION_RE = re.compile(r"^##\s+(.*\S)\s*$")
_LINK_RE = re.compile(r"^-\s+\[[^\]]*\]\((https?://[^)]+)\)")
_MARKER_RE = re.compile(r"^===/(.+?)===\s*$")


# ---------------------------------------------------------------------------
# Index style (## Section + - [title](url) bullets)
# ---------------------------------------------------------------------------

def slug_from_url(url: str, marker: str):
    """
    Return the page slug for a ``<...>{marker}<slug>.md`` URL, or ``None`` when
    the URL is not a Markdown content page under ``marker`` (e.g. a whole-file
    reference like ``llms-full.txt``). The slug keeps its full path so deep,
    leaf-colliding references stay unique.
    """
    i = url.find(marker)
    if i == -1:
        return None
    path = url[i + len(marker):]
    if not path.endswith(".md"):
        return None
    return path[: -len(".md")]


def parse_sections(text: str, marker: str, *, skip=frozenset()):
    """
    Parse index-style llms.txt into an ordered ``[(section_title, [slug, ...])]``.

      marker  URL path marker that identifies content pages ("/codex/", "/api/")
      skip    lowercased section titles to drop (their bullets are whole-file
              references, not content pages) — e.g. {"documentation sets"}

    Sections that end up with no content slugs are omitted.
    """
    sections = []
    title = None
    slugs = None
    for line in text.splitlines():
        m = _SECTION_RE.match(line)
        if m:
            if title is not None and slugs:
                sections.append((title, slugs))
            title = m.group(1)
            slugs = []
            continue
        if title is None:
            continue
        if title.strip().lower() in skip:
            continue
        m = _LINK_RE.match(line)
        if m:
            slug = slug_from_url(m.group(1), marker)
            if slug:
                slugs.append(slug)
    if title is not None and slugs:
        sections.append((title, slugs))
    return sections


# ---------------------------------------------------------------------------
# Concatenated style (===/<slug>=== delimited export)
# ---------------------------------------------------------------------------

def split_markers(text: str):
    """
    Split a ``===/<slug>===`` delimited export into ``[(slug, body), ...]`` in
    file order. Marker lines are dropped; each body is stripped of leading and
    trailing blank lines but otherwise preserved verbatim. Anything before the
    first marker is ignored.
    """
    pages = []
    slug = None
    buf = []
    for line in text.splitlines():
        m = _MARKER_RE.match(line)
        if m:
            if slug is not None:
                pages.append((slug, "\n".join(buf).strip("\n")))
            slug = m.group(1)
            buf = []
        elif slug is not None:
            buf.append(line)
    if slug is not None:
        pages.append((slug, "\n".join(buf).strip("\n")))
    return pages


def marker_order(text: str):
    """Ordered list of page slugs, as they appear in a concatenated export."""
    return [m.group(1) for line in text.splitlines()
            if (m := _MARKER_RE.match(line))]
