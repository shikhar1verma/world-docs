# AGENTS.md

Operating manual for coding agents (and humans) working in **world-docs**. This
file follows the [agents.md](https://agents.md/) open standard. `CLAUDE.md` is a
verbatim copy of this file — edit `AGENTS.md` and mirror it (a `wd verify` check
fails if they diverge).

---

## What this repo is

world-docs is a **local, offline, always-current mirror of framework/tool
documentation**, so that you can read authoritative docs straight from disk
instead of relying on (possibly stale) training data. Each supported technology
is fetched from its upstream source and laid out as ordered Markdown under
`docs/<source>/`.

The docs themselves are **not committed** — they are fully regenerable from the
code in `src/`. A fresh clone has no `docs/` until you build it (see below).

## Where to read the docs

After a build, docs live under `docs/<source>/`:

| Source | Read at | What it covers |
|--------|---------|----------------|
| `claude-code` | `docs/claude-code/` | Claude Code CLI / IDE |
| `codex` | `docs/codex/` | OpenAI Codex agent |
| `grok` | `docs/grok/` | Grok / xAI API |
| `hermes` | `docs/hermes/` | Hermes agent framework |
| `openai-api` | `docs/openai-api/` | OpenAI API (chat, assistants, realtime, …) |
| `openclaw` | `docs/openclaw/` | OpenClaw gateway |
| `openspec` | `docs/openspec/` | OpenSpec spec-driven development CLI (openspec.dev) |

Conventions when reading:
- Folders and files carry a `NN-` numeric prefix that mirrors the **upstream
  sidebar order** — read them in numeric order for the intended flow.
- Each source keeps its **nav/ordering reference** at its docs root
  (`nav.json`, `llms.txt`, `sidebars.ts`, `docs.json`, or
  `docs.sync.config.mjs`) — a good map of the set.
- Grep is your friend: `grep -ri "prompt caching" docs/claude-code/`.

If `docs/<source>/` is missing, it just hasn't been built yet — run
`wd refresh <source>`.

## The `wd` command

`wd` (world-docs) is the one entry point. Install with `pip install -e .` to get
the command, or call `python src/wd.py …` without installing.

```
wd                    status: every source + whether its docs are built
wd list               same as bare `wd`
wd refresh [source]   fetch + lay out + verify (all sources, or just one)
wd fetch   [source]   pull raw source into ._temp/ only
wd verify  [source]   check built docs are present & valid (fast, no network)
```

`[source]` is one of the folder names in the table above; omit it to act on all.
`python src/refresh_all.py` and `python src/verify_all.py` are thin shims for
`wd refresh` / `wd verify`.

## How it works — the fetch → refresh → verify pipeline

Every source implements the same three-stage contract as three small modules
under `src/sources/<source>/`, each calling the shared helpers in `src/common/`:

1. **`fetch.py` → `fetch()`** — the "clone" step. Pull the raw upstream into
   `._temp/<source>/`. Two mechanisms in use:
   - *HTTP*: download an `llms.txt`/`nav.json` index + each page's `.md` twin
     (`claude-code`, `codex`, `grok`, `openai-api`).
   - *git*: shallow `git clone --depth=1` of the docs repo (`hermes`, `openclaw`,
     `openspec`).
2. **`refresh.py` → `refresh()`** — the "layout" step. Read the nav index, build
   an ordered plan, wipe `docs/<source>/`, and copy pages in with `NN-` prefixes.
3. **`verify.py` → `verify()`** — the "self-heal detector". Assert the output is
   sane (min page count, required sections, no HTML-error/empty pages, nav ref
   present). Returns a list of problems; empty means pass.

`wd` is the only place that chains the stages. Sources are **discovered** from
`src/sources/` — there is no registry to update.

## Repo structure

```
src/
  wd.py               the CLI (discovers sources, chains stages, prints summary)
  refresh_all.py      shim -> wd refresh
  verify_all.py       shim -> wd verify
  common/             shared, stdlib-only helpers
    paths.py  http.py  llms_txt.py  layout.py  gitsource.py  verify.py
  sources/<source>/   fetch.py  refresh.py  verify.py  README.md
docs/<source>/        generated output (gitignored)
._temp/<source>/      raw fetch cache / shallow clones (gitignored)
pyproject.toml  .gitignore  README.md  AGENTS.md  CLAUDE.md
```

## Self-healing a broken source

Doc sites change shape; a fetcher will eventually break. The loop:

1. `wd verify <source>` — the failure names exactly what's wrong (too few pages,
   an HTML error page, a missing section, a missing nav reference).
2. Read `src/sources/<source>/README.md` — it documents where the docs come
   from, how extraction works, and the **exact fragile point** to inspect.
3. Patch the source-specific bit (a URL, a marker, a parser) in that source's
   `fetch.py`/`refresh.py`; shared HTTP/parse logic lives in `src/common/`.
4. `wd refresh <source>` then `wd verify <source>` until it passes.

## Adding a new source

1. `mkdir src/sources/<name>/` (use a hyphenated, lowercase name).
2. Add `fetch.py` (`fetch()`), `refresh.py` (`refresh()`), `verify.py`
   (`verify()`), and a `README.md` extraction note. Copy the closest existing
   source as a template and reuse `src/common/` helpers.
3. `wd refresh <name>` — it's discovered automatically; no registry to edit.

## Conventions (please keep these invariants)

- **Standard library only.** No runtime third-party dependencies —
  `pyproject.toml` has `dependencies = []`. If a source ever truly needs a
  package, add it there and explain why.
- **Python is the default implementation**, living directly in `src/`. Ports to
  other languages would go under `src/<lang>/` and must satisfy the same
  fetch→refresh→verify contract.
- **Source folder names are hyphenated** (`claude-code`) and match their
  `docs/<name>/` output; they're loaded by path, not imported as packages.
- **Never hand-edit `docs/`** — it is generated. Change `src/` and re-run.
- Keep `AGENTS.md` and `CLAUDE.md` identical.

## Roadmap

- An in-repo MCP server exposing the local docs to agents for fast lookup.
- Optional non-Python ports (JS/Go) under `src/<lang>/`.
