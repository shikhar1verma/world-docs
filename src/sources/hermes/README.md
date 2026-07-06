# hermes — extraction notes

How these docs are extracted and how to fix breakage. Output: `docs/hermes/`.

## Source
Hermes Agent docs in the public repo
**https://github.com/NousResearch/hermes-agent** — docs under `website/docs/`,
ordering in `website/sidebars.ts` (a Docusaurus config). Git extraction.

## Fetch (`fetch.py`)
Shallow `git clone --depth=1` (or `git pull --ff-only` on later runs) into
`._temp/hermes/`, via `common/gitsource.py`. Fails fast if `website/docs/` or
`website/sidebars.ts` is missing after the clone.

## Ordering & layout (`refresh.py`)
`sidebars.ts` is TypeScript, so it's parsed by a small hand-written JS
object-literal parser (`_JSParser` + `_preprocess`) to derive:
- **top-level section order** (from each top entry's primary directory), and
- **file order within each section**.

`website/docs/` is then copied into `docs/hermes/` with `NN-` prefixes applied to
top-level sections and to files within each section. `index.md`/`index.mdx` are
copied without a prefix; `sidebars.ts` is copied to the docs root as the ordering
reference. If parsing fails, refresh prints a warning and copies **without**
ordering rather than aborting.

## Fragile points
- **`sidebars.ts` syntax vs `_JSParser`.** The parser handles the current
  object-literal style; a new TS construct (spreads, function calls, imports used
  inline) can defeat it — you'll see `WARNING: sidebar parsing failed …` and
  unordered output.
- **Repo layout**: the `website/docs` + `website/sidebars.ts` paths (in
  `fetch.py`/`refresh.py`). If upstream relocates them, fetch raises.

## If it breaks
- "sidebar parsing failed" → open `._temp/hermes/website/sidebars.ts`, find the
  construct the parser choked on, and extend `_JSParser`/`_preprocess`.
- "expected …/website/… after clone" → the repo restructured; update `SIDEBAR`
  and `DOCS_SRC` in `fetch.py` (and `refresh.py`).

## Verify (`verify.py`)
Expects ≥ 250 pages, `sidebars.ts` present, no empty/HTML-error pages (sections
are sidebar-driven, so none are required by name). Run `wd verify hermes`.
