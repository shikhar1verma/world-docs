#!/usr/bin/env python3
"""
wd — the world-docs command line.

One small, memorable entry point for the whole repo:

    wd                    status: every source + whether its docs are built
    wd list               same as bare `wd`
    wd refresh [source]   fetch + lay out + verify (all sources, or just one)
    wd fetch   [source]   pull raw source into ._temp/ only
    wd verify  [source]   check built docs are present & valid (no network)

`[source]` is one of the folder names under src/sources/ (claude-code, codex,
grok, hermes, openai-api, openclaw). Omit it to act on every source.

Sources are discovered from src/sources/ and each exposes fetch()/refresh()/
verify() in its like-named module; `wd` is the only place that chains them.
"""

import argparse
import importlib.util
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))                     # make `common` importable

from common import paths, verify as cverify      # noqa: E402


# ---------------------------------------------------------------------------
# Source module loading
# ---------------------------------------------------------------------------

def _load(name: str, stage: str):
    """Load a source's fetch/refresh/verify module by path (names have hyphens)."""
    path = paths.source_dir(name) / f"{stage}.py"
    spec = importlib.util.spec_from_file_location(f"wd_{name}_{stage}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _resolve(source):
    """None -> all sources; a name -> [name] (validated); unknown -> exit 2."""
    sources = paths.list_sources()
    if source is None:
        return sources
    if source not in sources:
        print(f"unknown source: {source!r}", file=sys.stderr)
        print(f"valid sources: {', '.join(sources) or '(none)'}", file=sys.stderr)
        sys.exit(2)
    return [source]


def _agents_claude_drift():
    """Return a problem string if AGENTS.md and CLAUDE.md exist but differ."""
    a = paths.REPO_ROOT / "AGENTS.md"
    c = paths.REPO_ROOT / "CLAUDE.md"
    if not a.exists() or not c.exists():
        return None                              # bootstrap: not both present yet
    if a.read_text(encoding="utf-8") != c.read_text(encoding="utf-8"):
        return "CLAUDE.md differs from AGENTS.md (CLAUDE.md must be a verbatim copy)"
    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(source=None):
    sources = paths.list_sources()
    print(f"world-docs — {len(sources)} sources")
    for name in sources:
        n = cverify.count_pages(paths.docs_dir(name))
        print(f"  {name:<14} {str(n) + ' pages' if n else 'not built'}")
    print("\nRun `wd refresh [source]` to (re)build. Output goes to docs/<source>/.")


def cmd_fetch(source=None):
    for name in _resolve(source):
        print(f"=== fetch {name} ===")
        _load(name, "fetch").fetch()


def cmd_verify(source=None):
    names = _resolve(source)
    failed = []
    for name in names:
        problems = _load(name, "verify").verify()
        if problems:
            failed.append(name)
            print(f"FAIL {name}:")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"PASS {name} ({cverify.count_pages(paths.docs_dir(name))} pages)")
    if source is None:                           # whole-repo health: also check doc drift
        drift = _agents_claude_drift()
        if drift:
            failed.append("docs-sync")
            print(f"FAIL docs-sync:\n  - {drift}")
    if failed:
        sys.exit(1)


def cmd_refresh(source=None):
    names = _resolve(source)
    results = []
    for name in names:
        print(f"\n=== refresh {name} ===")
        try:
            _load(name, "fetch").fetch()
            _load(name, "refresh").refresh()
            problems = _load(name, "verify").verify()
        except Exception as e:                   # noqa: BLE001 — isolate per source
            problems = [f"{type(e).__name__}: {e}"]
            print(f"ERROR refreshing {name}: {e}")
        results.append((name, cverify.count_pages(paths.docs_dir(name)), problems))

    print("\nSummary:")
    any_fail = False
    for name, pages, problems in results:
        status = "PASS" if not problems else "FAIL"
        any_fail = any_fail or bool(problems)
        print(f"  {status}  {name:<14} {pages} pages")
        for p in problems:
            print(f"          - {p}")
    if any_fail:
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="wd", description="world-docs — local documentation mirror manager")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="list sources and whether their docs are built")
    for cmd, help_text in (
        ("refresh", "fetch + lay out + verify (all sources, or one)"),
        ("fetch", "pull raw source into ._temp/ only"),
        ("verify", "check built docs are present & valid"),
    ):
        sp = sub.add_parser(cmd, help=help_text)
        sp.add_argument("source", nargs="?", help="a single source (default: all)")

    args = parser.parse_args(argv)
    cmd = args.cmd or "list"                      # bare `wd` -> status
    source = getattr(args, "source", None)
    {"list": cmd_list, "fetch": cmd_fetch,
     "refresh": cmd_refresh, "verify": cmd_verify}[cmd](source)


if __name__ == "__main__":
    main()
