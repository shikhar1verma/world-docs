#!/usr/bin/env python3
"""
Refresh — lay out the cloned OpenSpec docs under docs/openspec/.

website/docs.sync.config.mjs is upstream's single source of truth for the docs
site: `docsDir` names the Markdown folder (currently ../docs-lab, relative to
website/) and `sections` lists every published page in sidebar order. We parse
that manifest and lay out exactly the pages openspec.dev/docs serves:

  docs/openspec/
    01-start/
      01-installation.md
      02-setup.md
    …
    04-reference/
      01-skills.md
      03-schemas/                 <- a folder entry (collapsible sidebar group)
        01-index.md
        02-schema-yaml.md
    docs.sync.config.mjs          (the ordering reference, copied verbatim)

Sections become NN-<slugified label> folders, folder entries NN-<folder name>,
and pages NN-<last slug segment>.md. Entries the manifest comments out are
held-back drafts the site does not serve, so they are not mirrored.

Page text is copied verbatim except for relative `*.md` links, which are
rewritten the way upstream's website/scripts/sync-docs.mjs rewrites them — but
to the local NN- paths instead of /docs routes. A link to a page the site does
not publish falls back to its source on GitHub, exactly as on the site.

FRAGILE POINT: docs.sync.config.mjs is a JavaScript module. We read its
`docsDir` and `sections` exports with a small JS-literal parser (_JSLiteral).
If upstream starts computing the manifest (spreads, variables, calls), parsing
raises with a line number and refresh aborts before touching docs/openspec/,
so the last good build survives. See this folder's README.md.

Assumes fetch() has already cloned the repo into ._temp/openspec/.
"""

from __future__ import annotations

import os
import posixpath
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import layout, paths                              # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
SYNC_CONFIG = TEMP / "website" / "docs.sync.config.mjs"
DEST = paths.docs_dir(NAME)

# Where links to unpublished pages point — the same fallback the site uses.
GITHUB_BLOB = "https://github.com/Fission-AI/OpenSpec/blob/main"


# ---------------------------------------------------------------------------
# docs.sync.config.mjs reader
# ---------------------------------------------------------------------------

_IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
_NUMBER_RE = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_KEYWORDS = {"true": True, "false": False, "null": None}
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v",
            "0": "\0", "\n": ""}


def _strip_comments(text: str) -> str:
    """
    Blank out // and /* */ comments (string-aware), keeping every newline so
    error line numbers still match the file. Commented-out manifest entries —
    upstream's held-back pages — vanish here.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "'\"`":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


class _JSLiteral:
    """
    Strict recursive-descent reader for the JavaScript literal subset the
    manifest uses (input must already be comment-free): objects with bare or
    quoted keys, arrays, '…' / "…" / `…` strings, numbers, true/false/null and
    trailing commas. Anything else — a spread, a variable, a call, a ${}
    interpolation — raises, so a manifest that turns computed fails loudly
    instead of being half-read.
    """

    def __init__(self, text: str, pos: int):
        self.t = text
        self.i = pos

    def fail(self, what: str):
        line = self.t.count("\n", 0, self.i) + 1
        near = self.t[self.i:self.i + 30].split("\n")[0]
        raise ValueError(f"docs.sync.config.mjs line {line}: {what} near {near!r}")

    def peek(self) -> str:
        while self.i < len(self.t) and self.t[self.i].isspace():
            self.i += 1
        return self.t[self.i] if self.i < len(self.t) else ""

    def value(self):
        c = self.peek()
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in ("'", '"', "`"):
            return self.string()
        m = _NUMBER_RE.match(self.t, self.i)
        if m:
            self.i = m.end()
            s = m.group(0)
            return float(s) if any(ch in s for ch in ".eE") else int(s)
        m = _IDENT_RE.match(self.t, self.i)
        if m and m.group(0) in _KEYWORDS:
            self.i = m.end()
            return _KEYWORDS[m.group(0)]
        self.fail("unsupported value (not a plain literal)")

    def string(self) -> str:
        q = self.t[self.i]
        self.i += 1
        buf = []
        while self.i < len(self.t):
            c = self.t[self.i]
            if c == q:
                self.i += 1
                return "".join(buf)
            if c == "\\":
                nxt = self.t[self.i + 1:self.i + 2]
                if nxt == "u":
                    buf.append(chr(int(self.t[self.i + 2:self.i + 6], 16)))
                    self.i += 6
                else:
                    buf.append(_ESCAPES.get(nxt, nxt))
                    self.i += 2
                continue
            if q == "`" and self.t.startswith("${", self.i):
                self.fail("template-literal interpolation")
            buf.append(c)
            self.i += 1
        self.fail("unterminated string")

    def key(self) -> str:
        if self.peek() in ("'", '"'):
            return self.string()
        m = _IDENT_RE.match(self.t, self.i)
        if not m:
            self.fail("unsupported object key")
        self.i = m.end()
        return m.group(0)

    def obj(self) -> dict:
        self.i += 1                                    # past '{'
        out = {}
        while self.peek() != "}":
            k = self.key()
            if self.peek() != ":":
                self.fail("expected ':' (shorthand properties / methods unsupported)")
            self.i += 1
            out[k] = self.value()
            if self.peek() == ",":
                self.i += 1
            elif self.peek() != "}":
                self.fail("expected ',' or '}'")
        self.i += 1                                    # past '}'
        return out

    def arr(self) -> list:
        self.i += 1                                    # past '['
        out = []
        while self.peek() != "]":
            out.append(self.value())
            if self.peek() == ",":
                self.i += 1
            elif self.peek() != "]":
                self.fail("expected ',' or ']'")
        self.i += 1                                    # past ']'
        return out


def _export(text: str, name: str):
    """Value of the top-level `export const <name> = <literal>` (comment-free text)."""
    m = re.search(rf"^[ \t]*export\s+const\s+{name}\s*=\s*", text, re.MULTILINE)
    if not m:
        raise ValueError(f"docs.sync.config.mjs: no `export const {name} = …` found")
    return _JSLiteral(text, m.end()).value()


def parse_manifest(path):
    """
    Read docs.sync.config.mjs -> (docs_dir, sections).

      docs_dir  the Markdown folder, relative to the manifest's directory
      sections  [{label, pages: [entry, …]}, …]; an entry is a page
                {source, slug} or a folder {folder, label, pages: [entry, …]}
    """
    text = _strip_comments(Path(path).read_text(encoding="utf-8"))
    docs_dir = _export(text, "docsDir")
    sections = _export(text, "sections")
    if not isinstance(docs_dir, str) or not docs_dir:
        raise ValueError("docs.sync.config.mjs: docsDir is not a non-empty string")
    if not isinstance(sections, list) or not sections:
        raise ValueError("docs.sync.config.mjs: sections is not a non-empty array")
    return docs_dir, sections


# ---------------------------------------------------------------------------
# Plan + link rewriting
# ---------------------------------------------------------------------------

def _leaf(path: str) -> str:
    """'schemas/spec-driven' -> 'spec-driven'."""
    return path.rstrip("/").split("/")[-1]


def _is_entry(e, *keys) -> bool:
    return isinstance(e, dict) and all(isinstance(e.get(k), str) for k in keys)


def build_plan(sections) -> list:
    """
    Flatten the manifest into an ordered [(dest_relpath, source), …]:

      dest_relpath  NN-<section>/[NN-<folder>/…]NN-<slug leaf>.md
      source        the page's path relative to docsDir (posix, normalized)
    """
    plan = []

    def walk(entries, prefix):
        for i, e in enumerate(entries, start=1):
            if _is_entry(e, "folder") and isinstance(e.get("pages"), list):
                walk(e["pages"], f"{prefix}/{i:02d}-{_leaf(e['folder'])}")
            elif _is_entry(e, "source", "slug"):
                plan.append((f"{prefix}/{i:02d}-{_leaf(e['slug'])}.md",
                             posixpath.normpath(e["source"])))
            else:
                raise ValueError(f"docs.sync.config.mjs: unrecognized page entry {e!r}")

    for si, section in enumerate(sections, start=1):
        if not (_is_entry(section, "label") and isinstance(section.get("pages"), list)):
            raise ValueError(f"docs.sync.config.mjs: unrecognized section {section!r}")
        walk(section["pages"], f"{si:02d}-{layout.slugify(section['label'])}")
    return plan


_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_KEEP_LINK_RE = re.compile(r"^(?:https?:|mailto:|#|/)")


def rewrite_links(markdown: str, source: str, dest: str, dest_by_source: dict,
                  repo_docs_dir: str) -> str:
    """
    Mirror sync-docs.mjs's rewriteLinks(), but target local files: a relative
    `*.md` link to a mirrored page becomes a relative path to its NN- file; a
    link to anything else (an unpublished draft, a repo file) becomes its
    GitHub URL. External, absolute, anchor-only and non-.md links are kept.
    """
    src_dir = posixpath.dirname(source)
    dest_dir = posixpath.dirname(dest)

    def repl(m):
        target = m.group(1)
        path, _, anchor = target.partition("#")
        if _KEEP_LINK_RE.match(target) or not path.lower().endswith(".md"):
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join(src_dir, path))
        suffix = f"#{anchor}" if anchor else ""
        if resolved in dest_by_source:
            return f"]({posixpath.relpath(dest_by_source[resolved], dest_dir)}{suffix})"
        repo_path = posixpath.normpath(posixpath.join(repo_docs_dir, resolved))
        return f"]({GITHUB_BLOB}/{repo_path}{suffix})"

    return _LINK_RE.sub(repl, markdown)


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def refresh() -> dict:
    if not SYNC_CONFIG.exists():
        raise FileNotFoundError(f"{SYNC_CONFIG} not found — run `wd fetch {NAME}` first.")

    print("Parsing docs.sync.config.mjs …")
    docs_dir, sections = parse_manifest(SYNC_CONFIG)
    plan = build_plan(sections)
    print(f"  docsDir {docs_dir!r}: {len(plan)} published pages in "
          f"{len(sections)} sections: {[s['label'] for s in sections]}")

    clone = TEMP.resolve()
    src_root = (SYNC_CONFIG.parent / docs_dir).resolve()
    if not (src_root.is_relative_to(clone) and src_root.is_dir()):
        raise FileNotFoundError(f"docsDir {docs_dir!r} is not a folder inside {clone}")

    # Upstream's site build fails on a manifest entry with no file, and so do
    # we — before wiping anything, so the previous docs/openspec/ survives.
    def ok(src):
        p = (src_root / src).resolve()
        return p.is_relative_to(src_root) and p.is_file()

    missing = [src for _, src in plan if not ok(src)]
    if missing:
        raise FileNotFoundError(
            f"manifest lists {len(missing)} page(s) not found under {docs_dir}: "
            f"{', '.join(missing)}")

    dest_by_source = {}
    for dest, src in plan:
        dest_by_source.setdefault(src, dest)           # first listing wins, as upstream
    repo_docs_dir = Path(os.path.relpath(src_root, clone)).as_posix()   # e.g. docs-lab

    layout.clean_dir(DEST)
    for dest, src in plan:
        text = (src_root / src).read_text(encoding="utf-8")
        out = DEST / dest
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rewrite_links(text, src, dest, dest_by_source, repo_docs_dir),
                       encoding="utf-8")
    shutil.copy2(SYNC_CONFIG, DEST / SYNC_CONFIG.name)  # ordering reference

    print(f"Done — {len(plan)} pages written to {DEST}")
    return {"written": len(plan), "missing": []}


def main() -> None:
    refresh()


if __name__ == "__main__":
    main()
