"""
Tiny HTTP layer used by the direct-fetch sources — stdlib ``urllib`` only.

Two things every HTTP-backed source needs:
  * ``get(url)``           — fetch one URL as text
  * ``download_slugs(...)``— fetch many page ``.md`` twins in parallel, writing
                             each to its mirrored path under a pages directory

Sources supply the URL/destination mapping (it differs per site) via callables,
so this module stays free of any site-specific knowledge.
"""

import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_USER_AGENT = "world-docs-fetch/1.0"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_WORKERS = 8


def get(url: str, *, user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = DEFAULT_TIMEOUT) -> str:
    """GET ``url`` and return the decoded body (utf-8, replacement on errors)."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def download_slugs(slugs, url_for, dest_for, *,
                   user_agent: str = DEFAULT_USER_AGENT,
                   timeout: int = DEFAULT_TIMEOUT,
                   max_workers: int = DEFAULT_MAX_WORKERS):
    """
    Download every slug's page in parallel.

      slugs     iterable of page slugs
      url_for   slug -> absolute URL to GET
      dest_for  slug -> destination Path to write (parents auto-created)

    Prints one line per failure and returns ``(ok_count, failures)`` where
    ``failures`` is ``[(slug, reason), ...]``. Never raises for a single bad
    page — the caller decides what a partial failure means.
    """
    def worker(slug):
        try:
            text = get(url_for(slug), user_agent=user_agent, timeout=timeout)
            dst = Path(dest_for(slug))
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
            return slug, True, len(text)
        except urllib.error.HTTPError as e:
            return slug, False, f"HTTP {e.code}"
        except Exception as e:                       # noqa: BLE001
            return slug, False, str(e)

    ok = 0
    failures = []
    slugs = list(slugs)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(worker, s): s for s in slugs}
        for fut in as_completed(futures):
            slug, success, info = fut.result()
            if success:
                ok += 1
            else:
                failures.append((slug, info))
                print(f"  ✗ {slug}: {info}")
    return ok, failures
