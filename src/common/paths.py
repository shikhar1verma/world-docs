"""
Path resolution shared by every source and by the ``wd`` CLI.

The repo layout is fixed:

    <repo>/
      src/common/paths.py   <- this file
      src/sources/<name>/    <- fetch.py / refresh.py / verify.py
      docs/<name>/           <- generated output (gitignored)
      ._temp/<name>/         <- raw fetch cache / shallow clones (gitignored)

so the repo root is two parents above this file and every per-source directory
is derived from the source's normalized name (its folder name under sources/).
"""

from pathlib import Path

# src/common/paths.py -> parents: [common, src, <repo root>]
REPO_ROOT = Path(__file__).resolve().parents[2]

SRC_DIR = REPO_ROOT / "src"
SOURCES_DIR = SRC_DIR / "sources"
DOCS_ROOT = REPO_ROOT / "docs"
TEMP_ROOT = REPO_ROOT / "._temp"


def docs_dir(name: str) -> Path:
    """Generated-docs directory for a source, e.g. ``docs/claude-code``."""
    return DOCS_ROOT / name


def temp_dir(name: str) -> Path:
    """Raw fetch/clone directory for a source, e.g. ``._temp/claude-code``."""
    return TEMP_ROOT / name


def source_dir(name: str) -> Path:
    """Script directory for a source, e.g. ``src/sources/claude-code``."""
    return SOURCES_DIR / name


def list_sources() -> list:
    """
    Every source name (folder under src/sources/), sorted. Adding a new source
    is just adding a folder here — the CLI discovers it automatically. Dot- and
    underscore-prefixed folders are ignored so scratch/helper dirs never count.
    """
    if not SOURCES_DIR.is_dir():
        return []
    return sorted(
        p.name
        for p in SOURCES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith((".", "_"))
    )
