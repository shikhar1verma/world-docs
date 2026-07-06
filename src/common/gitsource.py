"""
Git-backed fetching for sources whose docs live in a public repo (Hermes,
OpenClaw). A shallow ``--depth=1`` clone keeps ``._temp/<name>/`` small; on
later runs it fast-forwards instead of re-cloning.
"""

import subprocess
from pathlib import Path


def clone_or_pull(repo_url: str, dest, *, depth: int = 1) -> None:
    """
    Ensure ``dest`` is an up-to-date shallow checkout of ``repo_url``.

    If ``dest/.git`` exists, ``git pull --ff-only``; otherwise
    ``git clone --depth=<depth>``. Raises ``CalledProcessError`` if the clone
    fails (a pull that can't fast-forward only prints its message — the existing
    checkout is still usable and the refresh step will report stale/missing docs).
    """
    dest = Path(dest)
    if (dest / ".git").is_dir():
        print(f"Pulling {repo_url} …")
        r = subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            capture_output=True, text=True,
        )
        print(" ", r.stdout.strip() or r.stderr.strip() or "Already up to date.")
    else:
        print(f"Cloning {repo_url} (depth={depth}) …")
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", f"--depth={depth}", repo_url, str(dest)],
            check=True,
        )
