#!/usr/bin/env python3
"""
Fetch — OpenSpec docs → ._temp/openspec/.

The OpenSpec docs site (openspec.dev/docs) is generated from Markdown in the
public Fission-AI/OpenSpec repo, so the "clone" step is a shallow git
clone/pull (via common.gitsource). Upstream's manifest,
website/docs.sync.config.mjs, names the Markdown folder the site reads
(currently docs-lab/) and lists every published page in sidebar order.

FRAGILE POINT: the repo URL and the website/docs.sync.config.mjs location. If
upstream moves them, patch the constants here (see this folder's README.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # make `common` importable

from common import gitsource, paths                           # noqa: E402

NAME = Path(__file__).resolve().parent.name
TEMP = paths.temp_dir(NAME)
REPO_URL = "https://github.com/Fission-AI/OpenSpec.git"
SYNC_CONFIG = TEMP / "website" / "docs.sync.config.mjs"


def fetch() -> None:
    gitsource.clone_or_pull(REPO_URL, TEMP, depth=1)
    if not SYNC_CONFIG.exists():
        raise FileNotFoundError(
            f"expected {SYNC_CONFIG} after clone — repo layout may have changed "
            f"(see src/sources/{NAME}/README.md)"
        )
    print(f"Done — OpenSpec repo ready at {TEMP}")


def main() -> None:
    fetch()


if __name__ == "__main__":
    main()
