# openclaw — extraction notes

How these docs are extracted and how to fix breakage. Output: `docs/openclaw/`.

## Source
OpenClaw docs in the public repo **https://github.com/openclaw/openclaw** — docs
under `docs/`, ordering in `docs/docs.json` (Mintlify navigation). Git extraction.

## Fetch (`fetch.py`)
Shallow `git clone --depth=1` (or `git pull --ff-only` on later runs) into
`._temp/openclaw/`, via `common/gitsource.py`. Fails fast if `docs/docs.json` is
missing after the clone.

## Ordering & layout (`refresh.py`)
`parse_nav()` reads `docs.json` at
`navigation.languages[0].tabs[].groups[].pages[]` and flattens it to a top-level
section order plus per-section page order. `docs/` is copied into
`docs/openclaw/` with `NN-` prefixes on top-level sections and on files within
each section. Config/meta files (`docs.json`, `style.css`,
`nav-tabs-underline.js`, `CLAUDE.md`, `AGENTS.md`, `index.md/.mdx`) and hidden
dirs (`.generated`, `.i18n`) are copied verbatim without numbering. `docs.json`
at the docs root is the ordering reference.

## Fragile points
- **The Mintlify nav schema** — `navigation.languages[0].tabs[].groups[].pages[]`
  in `parse_nav()`. If OpenClaw restructures `docs.json` (e.g. drops the
  `languages` layer), `parse_nav` finds 0 sections.
- **Repo layout**: the `docs/` + `docs/docs.json` paths in `fetch.py`.

## If it breaks
- "0 top-level nav sections found" → open `._temp/openclaw/docs/docs.json`, see
  how `navigation` is now shaped, and update `parse_nav()`.
- "expected …/docs/docs.json after clone" → the repo restructured; update
  `DOCS_SRC`/`DOCS_JSON` in `fetch.py`.

## Verify (`verify.py`)
Expects ≥ 450 pages, `docs.json` present, no empty/HTML-error pages (sections are
docs.json-driven, so none are required by name). Run `wd verify openclaw`.
