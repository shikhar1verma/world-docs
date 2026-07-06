"""
world-docs shared helpers.

Every documentation source under ``src/sources/<name>/`` implements the same
three-stage contract — ``fetch`` (pull raw source into ``._temp/<name>/``),
``refresh`` (lay it out under ``docs/<name>/``), and ``verify`` (assert the
output is sane) — by calling into the small, stdlib-only helpers collected here:

  paths      resolve repo root, ``docs/<name>/`` and ``._temp/<name>/``
  http       one-shot GET + parallel per-page download
  llms_txt   parse llms.txt / nav indexes into ordered slug lists
  layout     slugify, wipe a dir, copy an ordered file plan, copy reference files
  gitsource  shallow clone-or-pull for git-backed sources
  verify     reusable output checks (min pages, no error pages, required sections)

Nothing here imports a third-party package — that is a deliberate invariant of
the whole repo (see AGENTS.md).
"""

__all__ = ["paths", "http", "llms_txt", "layout", "gitsource", "verify"]
