"""
Layout helpers — turn a fetched ``._temp/<name>/`` tree into an ordered,
``NN-`` prefixed ``docs/<name>/`` tree.

Because scripts and generated docs now live in *separate* trees, the "clean"
step can wipe ``docs/<name>/`` wholesale (there are no scripts to preserve),
which is why ``clean_dir`` is unconditional. Sources build an ordered *plan*
(a list of ``(dest_relpath, src_abspath)`` pairs) and hand it to ``apply_plan``.
"""

import re
import shutil
from pathlib import Path

_APOSTROPHES = ("'", "’")            # straight + curly


def slugify(name: str) -> str:
    """'Getting started' -> 'getting-started'; 'What's New' -> 'whats-new'."""
    s = name.lower()
    for a in _APOSTROPHES:
        s = s.replace(a, "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def clean_dir(path) -> None:
    """Remove ``path`` entirely and recreate it empty."""
    p = Path(path)
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def apply_plan(dest_dir, plan):
    """
    Copy an ordered file plan into ``dest_dir``.

      plan  iterable of ``(dest_relpath, src_abspath)`` — ``dest_relpath`` carries
            the ``NN-`` prefixes; ``src_abspath`` is the fetched page.

    Missing sources are skipped (not fatal — a page can be listed in nav yet not
    downloaded). Returns ``(written, missing)`` where ``missing`` is the list of
    ``dest_relpath`` whose source did not exist.
    """
    dest_dir = Path(dest_dir)
    written = 0
    missing = []
    for dst_rel, src in plan:
        src = Path(src)
        if not src.exists():
            missing.append(dst_rel)
            continue
        dst = dest_dir / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written += 1
    return written, missing


def copy_refs(src_dir, dest_dir, names):
    """
    Copy each whole-file reference (nav.json / llms.txt / llms-full.txt / …)
    from ``src_dir`` to ``dest_dir`` without a numeric prefix. Missing files are
    silently skipped. Returns the list of names actually copied.
    """
    src_dir = Path(src_dir)
    dest_dir = Path(dest_dir)
    copied = []
    for name in names:
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, dest_dir / name)
            copied.append(name)
    return copied
