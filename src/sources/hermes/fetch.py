#!/usr/bin/env python3
"""
Fetch — Hermes Agent docs → ._temp/hermes/.

Hermes docs live in a public GitHub repo, so the "clone" step is a shallow
git clone/pull (via common.gitsource). The docs themselves are under
website/docs/ and the sidebar ordering under website/sidebars.ts.

FRAGILE POINT: the repo URL and the website/docs + website/sidebars.ts layout.
If upstream moves them, patch the constants here (see this folder's README.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import gitsource, paths                           # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
REPO_URL = "https://github.com/NousResearch/hermes-agent.git"
SIDEBAR = TEMP / "website" / "sidebars.ts"
DOCS_SRC = TEMP / "website" / "docs"


def fetch() -> None:
    gitsource.clone_or_pull(REPO_URL, TEMP, depth=1)
    if not SIDEBAR.exists() or not DOCS_SRC.is_dir():
        raise FileNotFoundError(
            f"expected {SIDEBAR} and {DOCS_SRC} after clone — repo layout may "
            f"have changed (see src/sources/{NAME}/README.md)"
        )
    print(f"Done — Hermes repo ready at {TEMP}")


def main() -> None:
    fetch()


if __name__ == "__main__":
    main()
