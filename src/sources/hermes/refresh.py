#!/usr/bin/env python3
"""
Refresh — lay out the cloned Hermes docs under docs/hermes/.

Parses website/sidebars.ts (a Docusaurus config) to derive ordering, then
copies website/docs/ into docs/hermes/ applying NN- prefixes to top-level
sections and to files within each section.

FRAGILE POINT: sidebars.ts is TypeScript; we parse it with a small hand-written
JS object-literal parser (_JSParser below). If the Docusaurus config adopts
syntax the parser doesn't handle, parse_sidebar() raises and we fall back to
copying without ordering (a loud warning is printed). See this folder's README.md.

Assumes fetch() has already cloned the repo into ._temp/hermes/.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import layout, paths                              # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
DOCS_SRC = TEMP / "website" / "docs"
SIDEBAR = TEMP / "website" / "sidebars.ts"
DEST = paths.docs_dir(NAME)

# Root files copied without a numeric prefix
NO_PREFIX = {"index.mdx", "index.md"}


# ---------------------------------------------------------------------------
# Minimal JavaScript / TypeScript object-literal parser
# ---------------------------------------------------------------------------

class _JSParser:
    """
    Recursive-descent parser for the JS/TS object-literal syntax used in
    sidebars.ts. Handles single/double-quoted strings, unquoted identifiers as
    object keys, nested objects/arrays, // and /* */ comments, and the
    TypeScript-specific bits we strip before parsing.
    """

    def __init__(self, text: str):
        self.t = text
        self.i = 0

    def _skip(self):
        while self.i < len(self.t):
            c = self.t[self.i]
            if c in " \t\n\r":
                self.i += 1
            elif self.t[self.i:self.i + 2] == "//":
                while self.i < len(self.t) and self.t[self.i] != "\n":
                    self.i += 1
            elif self.t[self.i:self.i + 2] == "/*":
                end = self.t.find("*/", self.i + 2)
                self.i = (end + 2) if end != -1 else len(self.t)
            else:
                break

    def _string(self) -> str:
        q = self.t[self.i]; self.i += 1
        buf = []
        while self.i < len(self.t):
            c = self.t[self.i]
            if c == "\\" and self.i + 1 < len(self.t):
                self.i += 1
                buf.append(self.t[self.i])
                self.i += 1
            elif c == q:
                self.i += 1
                break
            else:
                buf.append(c); self.i += 1
        return "".join(buf)

    def _ident(self) -> str:
        start = self.i
        while self.i < len(self.t) and (self.t[self.i].isalnum() or self.t[self.i] in "_-"):
            self.i += 1
        return self.t[start:self.i]

    def _value(self):
        self._skip()
        if self.i >= len(self.t):
            return None
        c = self.t[self.i]
        if c in ('"', "'", "`"):
            return self._string()
        if c == "{":
            return self._object()
        if c == "[":
            return self._array()
        if self.t[self.i:self.i + 4] == "true":
            self.i += 4; return True
        if self.t[self.i:self.i + 5] == "false":
            self.i += 5; return False
        if self.t[self.i:self.i + 4] == "null":
            self.i += 4; return None
        if c.isalpha() or c == "_":
            return self._ident()
        self.i += 1
        return None

    def _object(self) -> dict:
        assert self.t[self.i] == "{"; self.i += 1
        obj: dict = {}
        while self.i < len(self.t):
            self._skip()
            if self.i >= len(self.t) or self.t[self.i] == "}":
                if self.i < len(self.t): self.i += 1
                break
            if self.t[self.i] == ",":
                self.i += 1; continue
            if self.t[self.i] in ('"', "'"):
                key = self._string()
            else:
                key = self._ident()
            self._skip()
            if self.i < len(self.t) and self.t[self.i] == ":":
                self.i += 1
            val = self._value()
            if key:
                obj[key] = val
        return obj

    def _array(self) -> list:
        assert self.t[self.i] == "["; self.i += 1
        arr: list = []
        while self.i < len(self.t):
            self._skip()
            if self.i >= len(self.t) or self.t[self.i] == "]":
                if self.i < len(self.t): self.i += 1
                break
            if self.t[self.i] == ",":
                self.i += 1; continue
            v = self._value()
            if v is not None:
                arr.append(v)
        return arr


def _preprocess(text: str) -> str:
    """Strip TypeScript-only syntax so the parser can focus on JS."""
    text = re.sub(r"^import\s+type\s+.*?;$", "", text, flags=re.MULTILINE)
    text = re.sub(r":\s*SidebarsConfig", "", text)
    text = re.sub(r"^export\s+default\s+\w+\s*;$", "", text, flags=re.MULTILINE)
    return text


def parse_sidebar(sidebar_path):
    """Parse sidebars.ts -> (top_order, dir_file_order)."""
    raw = Path(sidebar_path).read_text()
    text = _preprocess(raw)

    m = re.search(r"const\s+sidebars\s*=\s*\{", text)
    if not m:
        raise ValueError("Could not find 'const sidebars = {' in sidebars.ts")

    brace_start = m.end() - 1                 # points at '{'
    parser = _JSParser(text[brace_start:])
    sidebars_obj = parser._object()
    return _extract_order(sidebars_obj.get("docs", []))


def _primary_dir(item) -> str | None:
    """Top-level directory that 'owns' this sidebar entry (its first leaf path)."""
    if isinstance(item, str):
        return item.split("/")[0]
    if isinstance(item, dict):
        for sub in item.get("items", []):
            d = _primary_dir(sub)
            if d:
                return d
    return None


def _all_pages(item):
    """Recursively yield every page path string in a sidebar item."""
    if isinstance(item, str):
        yield item
    elif isinstance(item, dict):
        for sub in item.get("items", []):
            yield from _all_pages(sub)


def _extract_order(items: list):
    top_order: list[str] = []
    dir_file_order: dict = {}
    seen_top: set[str] = set()

    for item in items:                        # iterate top-level entries only
        primary = _primary_dir(item)
        if primary and primary not in seen_top:
            seen_top.add(primary)
            top_order.append(primary)

        for page in _all_pages(item):
            top = page.split("/")[0]
            stem = page.split("/")[-1]
            dir_file_order.setdefault(top, [])
            if stem not in dir_file_order[top]:
                dir_file_order[top].append(stem)

    return top_order, dir_file_order


# ---------------------------------------------------------------------------
# Copy helpers
# ---------------------------------------------------------------------------

def _stem(filename: str) -> str:
    for ext in (".mdx", ".md"):
        if filename.endswith(ext):
            return filename[: -len(ext)]
    return filename


def _copy_dir_with_numbering(src: str, dst: str, file_num: dict):
    os.makedirs(dst, exist_ok=True)
    for item in sorted(os.listdir(src)):
        src_p = os.path.join(src, item)
        if os.path.isdir(src_p):
            shutil.copytree(src_p, os.path.join(dst, item), dirs_exist_ok=False)
        else:
            stem = _stem(item)
            ext = item[len(stem):]
            dst_name = (file_num[stem] + ext) if stem in file_num else item
            shutil.copy2(src_p, os.path.join(dst, dst_name))


def copy_docs(src_docs: str, dest: str, top_order: list, dir_file_order: dict):
    top_num = {name: f"{i:02d}-{name}" for i, name in enumerate(top_order, start=1)}
    dir_file_num = {
        top: {stem: f"{i:02d}-{stem}" for i, stem in enumerate(stems, start=1)}
        for top, stems in dir_file_order.items()
    }

    total = 0
    for src_item in sorted(os.listdir(src_docs)):
        src_p = os.path.join(src_docs, src_item)
        stem = _stem(src_item)

        if src_item in NO_PREFIX:
            shutil.copy2(src_p, os.path.join(dest, src_item))
            total += 1
            continue

        if src_item.startswith("."):
            dst_p = os.path.join(dest, src_item)
            if os.path.isdir(src_p):
                shutil.copytree(src_p, dst_p, dirs_exist_ok=False)
            else:
                shutil.copy2(src_p, dst_p)
            total += 1
            continue

        if stem in top_num:
            dst_name = top_num[stem] if os.path.isdir(src_p) else top_num[stem] + src_item[len(stem):]
        else:
            dst_name = src_item

        dst_p = os.path.join(dest, dst_name)
        if os.path.isdir(src_p):
            _copy_dir_with_numbering(src_p, dst_p, dir_file_num.get(stem, {}))
        else:
            shutil.copy2(src_p, dst_p)
        total += 1

    return total


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def refresh() -> dict:
    if not SIDEBAR.exists():
        raise FileNotFoundError(f"{SIDEBAR} not found — run `wd fetch {NAME}` first.")

    print("Parsing sidebars.ts …")
    try:
        top_order, dir_file_order = parse_sidebar(SIDEBAR)
    except Exception as exc:                   # noqa: BLE001
        print(f"  WARNING: sidebar parsing failed ({exc}); copying without ordering.")
        top_order, dir_file_order = [], {}
    print(f"  {len(top_order)} top-level sections: {top_order}")

    layout.clean_dir(DEST)
    print("Copying docs with ordering …")
    total = copy_docs(str(DOCS_SRC), str(DEST), top_order, dir_file_order)

    shutil.copy2(SIDEBAR, os.path.join(str(DEST), "sidebars.ts"))   # ordering reference
    total += 1

    pages = sum(1 for p in DEST.rglob("*") if p.suffix in (".md", ".mdx"))
    print(f"Done — {total} items ({pages} pages) written to {DEST}")
    return {"written": pages, "items": total, "missing": []}


def main() -> None:
    refresh()


if __name__ == "__main__":
    main()
