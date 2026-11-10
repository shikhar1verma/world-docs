# world-docs

**A local, self-healing mirror of framework & tool documentation — for humans and coding agents.**

world-docs fetches the official documentation of the tools you use and lays it
out as clean, ordered Markdown on your disk under `docs/<source>/`. Point an
agent at the folder (or grep it yourself) and get authoritative, current answers
instead of guesses from stale training data — fully offline, once built.

The docs are **not committed to git**. They're regenerable from the code in
`src/`, so the repo stays tiny and the docs stay fresh: clone, run one command,
and the full doc set rebuilds locally.

---

## Supported sources

| Source | Upstream | Fetch method | Pages* |
|--------|----------|--------------|-------:|
| `claude-code` | code.claude.com | HTTP (nav in page HTML + `.md` twins) | ~160 |
| `codex` | developers.openai.com/codex | HTTP (`llms.txt` index + `.md` twins) | ~95 |
| `grok` | docs.x.ai | HTTP (single concatenated `llms.txt`) | ~140 |
| `hermes` | github.com/NousResearch/hermes-agent | git clone (`sidebars.ts`) | ~350 |
| `openai-api` | developers.openai.com/api | HTTP (`llms.txt` index + `.md` twins) | ~380 |
| `openclaw` | github.com/openclaw/openclaw | git clone (`docs.json`) | ~685 |
| `openspec` | github.com/Fission-AI/OpenSpec (openspec.dev/docs) | git clone (`docs.sync.config.mjs`) | ~20 |

\* approximate; the whole point is that a refresh pulls whatever is current.

## Quickstart

```bash
git clone https://github.com/shikhar1verma/world-docs.git
cd world-docs
pip install -e .          # gives you the `wd` command (no other dependencies)

wd refresh                # fetch + build every source into docs/
# ...or just one:
wd refresh grok

wd list                   # see what's built
```

No install needed if you prefer: `python src/refresh_all.py` does the same as
`wd refresh`. Requires **Python 3.9+** and `git` (for the three git-based sources).

## The `wd` command

```
wd                    status: every source + whether its docs are built
wd list               same as bare `wd`
wd refresh [source]   fetch + lay out + verify (all sources, or just one)
wd fetch   [source]   pull raw source into ._temp/ only
wd verify  [source]   check built docs are present & valid (fast, no network)
```

`[source]` is one of the names in the table above; omit it to act on all sources.

## How it works

Each source runs a three-stage pipeline (see `src/sources/<source>/`):

1. **fetch** — pull the raw upstream into `._temp/<source>/` (HTTP download or a
   shallow `git clone`).
2. **refresh** — read the upstream's navigation, then copy the pages into
   `docs/<source>/` with `NN-` numeric prefixes that mirror the live sidebar
   order.
3. **verify** — assert the result looks sane (enough pages, expected sections,
   no empty/HTML-error pages, nav reference present).

`wd` chains these and prints a per-source PASS/FAIL summary.

## Repo structure

```
src/
  wd.py                 the CLI
  refresh_all.py        shim -> wd refresh
  verify_all.py         shim -> wd verify
  common/               shared, stdlib-only helpers (http, llms_txt, layout, git, verify)
  sources/<source>/     fetch.py + refresh.py + verify.py + README.md (extraction note)
docs/<source>/          generated output (gitignored)
._temp/<source>/        raw fetch cache / shallow clones (gitignored)
pyproject.toml  .gitignore  README.md  AGENTS.md  CLAUDE.md
```

## Why the docs aren't committed

Everything under `docs/` and `._temp/` is regenerable from `src/`, so committing
it would just bloat the repo and go stale. `.gitignore` keeps them out; `wd
refresh` rebuilds them. What *is* committed is the small amount of code that
recreates the docs — which is the whole idea.

## Adding a new source

1. Create `src/sources/<name>/` (hyphenated, lowercase).
2. Add `fetch.py`, `refresh.py`, `verify.py`, and a `README.md` extraction note —
   copy the closest existing source and reuse the helpers in `src/common/`.
3. `wd refresh <name>` — it's discovered automatically; there's no registry to edit.

See [AGENTS.md](AGENTS.md) for the full contract.

## Self-healing

Doc sites change, and a fetcher will eventually break. When it does:

- `wd verify <source>` fails **loudly and specifically** (e.g. "only 3 pages
  found (expected ≥ 90)", "looks like an HTML error page").
- Each `src/sources/<source>/README.md` documents the exact fragile point and how
  to re-patch it.

So a broken source is caught automatically and cheap to fix.

## Multi-language

Python is the default implementation and lives in `src/`. The
fetch→refresh→verify contract is language-agnostic, so ports in other languages
(JS, Go, …) can live under `src/<lang>/` later without changing the layout or the
`docs/` output. Everything today is **Python standard library only** — nothing to
install beyond Python itself.

## Roadmap

- A small in-repo **MCP server** so agents can query the local docs directly.
- Optional non-Python ports of the fetchers.

## License

MIT — see [LICENSE](LICENSE).
