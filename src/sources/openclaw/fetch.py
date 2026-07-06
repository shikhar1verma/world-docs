#!/usr/bin/env python3
"""
Fetch — OpenClaw docs → ._temp/openclaw/.

OpenClaw docs live in a public GitHub repo, so the "clone" step is a shallow
git clone/pull (via common.gitsource). Docs are under docs/ and the Mintlify
navigation under docs/docs.json.

FRAGILE POINT: the repo URL and the docs/ + docs/docs.json layout. If upstream
moves them, patch the constants here (see this folder's README.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import gitsource, paths                           # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
REPO_URL = "https://github.com/openclaw/openclaw.git"
DOCS_SRC = TEMP / "docs"
DOCS_JSON = DOCS_SRC / "docs.json"


def fetch() -> None:
    gitsource.clone_or_pull(REPO_URL, TEMP, depth=1)
    if not DOCS_JSON.exists():
        raise FileNotFoundError(
            f"expected {DOCS_JSON} after clone — repo layout may have changed "
            f"(see src/sources/{NAME}/README.md)"
        )
    print(f"Done — OpenClaw repo ready at {TEMP}")


def main() -> None:
    fetch()


if __name__ == "__main__":
    main()
