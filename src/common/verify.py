"""
Reusable output checks — the self-healing layer.

A source's ``verify.py`` supplies the *expected* values (minimum page count,
required top-level sections, nav reference filename) and composes the checks
below. Every check returns a list of human-readable problem strings (empty means
pass), so ``verify()`` can simply concatenate them. When a doc site changes its
shape and a fetcher silently degrades, these checks turn that into a loud,
specific failure that points at what to re-patch (see each source's README.md).
"""

import re
from pathlib import Path

MD_EXTS = (".md", ".mdx")
_NUM_PREFIX_RE = re.compile(r"^\d{2,}-")


def strip_num(name: str) -> str:
    """'01-getting-started' -> 'getting-started'."""
    return _NUM_PREFIX_RE.sub("", name)


def iter_pages(docs_dir):
    """Yield every Markdown page Path under ``docs_dir`` (recursively)."""
    root = Path(docs_dir)
    if not root.is_dir():
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in MD_EXTS:
            yield p


def count_pages(docs_dir) -> int:
    return sum(1 for _ in iter_pages(docs_dir))


def check_built(name: str, docs_dir) -> list:
    """Fatal precheck: the docs dir must exist and be non-empty."""
    d = Path(docs_dir)
    if not d.is_dir():
        return [f"docs/{name}/ does not exist — run `wd refresh {name}`"]
    if not any(d.iterdir()):
        return [f"docs/{name}/ is empty — run `wd refresh {name}`"]
    return []


def check_min_pages(docs_dir, minimum: int) -> list:
    n = count_pages(docs_dir)
    if n < minimum:
        return [f"only {n} pages found (expected ≥ {minimum}) — "
                f"fetch may have partially failed"]
    return []


def check_no_error_pages(docs_dir) -> list:
    """Reject zero-byte pages and pages that are actually HTML error responses."""
    problems = []
    for p in iter_pages(docs_dir):
        try:
            if p.stat().st_size == 0:
                problems.append(f"{p.name}: empty file")
                continue
            head = p.read_text(encoding="utf-8", errors="replace")[:512].lstrip().lower()
        except OSError as e:                         # noqa: BLE001
            problems.append(f"{p.name}: unreadable ({e})")
            continue
        if head.startswith("<!doctype") or head.startswith("<html"):
            problems.append(f"{p.name}: looks like an HTML error page, not Markdown")
    return problems


def check_required_sections(docs_dir, required) -> list:
    """
    Every name in ``required`` must be present as a top-level entry, comparing
    with the ``NN-`` prefix stripped (so 'getting-started' matches the folder
    '01-getting-started').
    """
    d = Path(docs_dir)
    if not d.is_dir():
        return [f"cannot check sections: {d} missing"]
    present = {strip_num(p.name) for p in d.iterdir()}
    missing = [r for r in required if r not in present]
    if missing:
        return [f"missing expected top-level section(s): {', '.join(missing)}"]
    return []


def check_nav_ref(docs_dir, names) -> list:
    """At least one of ``names`` (the nav/ordering reference file) must exist."""
    d = Path(docs_dir)
    if any((d / n).exists() for n in names):
        return []
    return [f"nav reference missing (expected one of: {', '.join(names)})"]


def run(name, docs_dir, *, min_pages, nav_refs, required_sections=()) -> list:
    """
    Standard verification pipeline every source reuses. Returns the combined list
    of problems (empty = pass). If the docs aren't built at all, returns just that
    (the later checks would be noise). ``required_sections`` is optional because
    sources with many dynamic top-level folders can't name stable anchors.
    """
    problems = check_built(name, docs_dir)
    if problems:
        return problems
    problems += check_min_pages(docs_dir, min_pages)
    if required_sections:
        problems += check_required_sections(docs_dir, required_sections)
    problems += check_nav_ref(docs_dir, nav_refs)
    problems += check_no_error_pages(docs_dir)
    return problems
