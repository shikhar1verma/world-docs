#!/usr/bin/env python3
"""
Refresh — lay out the cloned OpenClaw docs under docs/openclaw/.

Parses docs/docs.json (Mintlify navigation) to derive ordering, then copies
docs/ into docs/openclaw/ applying NN- prefixes to top-level sections and to
files within each section. Config/meta files (docs.json, style.css, …) and
hidden dirs (.generated, .i18n) are copied verbatim without numbering.

FRAGILE POINT: the Mintlify navigation schema
(navigation.languages[0].tabs[].groups[].pages[]). If docs.json restructures its
nav, patch parse_nav() (see this folder's README.md).

Assumes fetch() has already cloned the repo into ._temp/openclaw/.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import layout, paths                              # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
DOCS_SRC = TEMP / "docs"
DOCS_JSON = DOCS_SRC / "docs.json"
DEST = paths.docs_dir(NAME)

# Files placed without any numeric prefix (config/meta that never move)
NO_PREFIX = {"docs.json", "CLAUDE.md", "AGENTS.md", "style.css",
             "nav-tabs-underline.js", "index.md", "index.mdx"}


# ---------------------------------------------------------------------------
# Navigation parser
# ---------------------------------------------------------------------------

def _collect_pages(pages: list) -> list:
    """Recursively flatten pages from a Mintlify navigation node."""
    out = []
    for p in pages:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            out.extend(_collect_pages(p.get("pages", [])))
    return out


def parse_nav(docs_json_path):
    """
    Return (top_order, dir_file_order).

    top_order       : top-level names in first-appearance order
    dir_file_order  : dict[top_name -> list[full_page_path]]
    """
    config = json.loads(Path(docs_json_path).read_text())
    tabs = (config.get("navigation", {})
                  .get("languages", [{}])[0]
                  .get("tabs", []))

    all_pages: list[str] = []
    for tab in tabs:
        for group in tab.get("groups", []):
            all_pages.extend(_collect_pages(group.get("pages", [])))

    top_order: list[str] = []
    dir_file_order: dict = {}
    seen_top: set[str] = set()

    for page in all_pages:
        top = page.split("/")[0]
        if top not in seen_top:
            seen_top.add(top)
            top_order.append(top)
        dir_file_order.setdefault(top, [])
        if page not in dir_file_order[top]:
            dir_file_order[top].append(page)

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
    """Copy src/ to dst/, numbering immediate .md/.mdx children; nested dirs verbatim."""
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

    dir_file_num: dict = {}
    for top, pages in dir_file_order.items():
        file_num: dict = {}
        for i, page in enumerate(pages, start=1):
            stem = page.split("/")[-1]
            if stem not in file_num:
                file_num[stem] = f"{i:02d}-{stem}"
        dir_file_num[top] = file_num

    total = 0
    for src_item in sorted(os.listdir(src_docs)):
        src_p = os.path.join(src_docs, src_item)
        stem = _stem(src_item)

        # Config / meta files — copy as-is
        if src_item in NO_PREFIX:
            dst = os.path.join(dest, src_item)
            if os.path.isdir(src_p):
                shutil.copytree(src_p, dst, dirs_exist_ok=False)
            else:
                shutil.copy2(src_p, dst)
            total += 1
            continue

        # Hidden / generated dirs (e.g. .generated, .i18n) — copy as-is
        if src_item.startswith("."):
            dst = os.path.join(dest, src_item)
            if os.path.isdir(src_p):
                shutil.copytree(src_p, dst, dirs_exist_ok=False)
            else:
                shutil.copy2(src_p, dst)
            total += 1
            continue

        if stem in top_num:
            dst_name = top_num[stem]
            if not os.path.isdir(src_p):           # root .md file
                dst_name = top_num[stem] + src_item[len(stem):]
        else:
            dst_name = src_item                    # not in nav — original name

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
    if not DOCS_JSON.exists():
        raise FileNotFoundError(f"{DOCS_JSON} not found — run `wd fetch {NAME}` first.")

    print("Parsing docs.json navigation …")
    top_order, dir_file_order = parse_nav(DOCS_JSON)
    print(f"  {len(top_order)} top-level nav sections found")

    layout.clean_dir(DEST)
    print("Copying docs with ordering …")
    total = copy_docs(str(DOCS_SRC), str(DEST), top_order, dir_file_order)

    pages = sum(1 for p in DEST.rglob("*") if p.suffix in (".md", ".mdx"))
    print(f"Done — {total} items ({pages} pages) written to {DEST}")
    return {"written": pages, "items": total, "missing": []}


def main() -> None:
    refresh()


if __name__ == "__main__":
    main()
