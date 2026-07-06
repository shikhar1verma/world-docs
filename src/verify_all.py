#!/usr/bin/env python3
"""
Thin shim: `python src/verify_all.py [source]` == `wd verify [source]`.

Kept so the repo works before `pip install -e .` makes the `wd` command
available. All real logic lives in wd.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `wd` importable

import wd  # noqa: E402

if __name__ == "__main__":
    wd.main(["verify", *sys.argv[1:]])
