# openspec — extraction notes

How these docs are extracted and how to fix breakage. Output: `docs/openspec/`.

## Source
OpenSpec docs, published at **https://openspec.dev/docs**, are generated from
Markdown in the public repo **https://github.com/Fission-AI/OpenSpec**. The
manifest `website/docs.sync.config.mjs` names the Markdown folder the site reads
(`docsDir`, currently `docs-lab/`) and lists every published page with its
sidebar section and order (`sections`). Git extraction.

## Fetch (`fetch.py`)
Shallow `git clone --depth=1` (or `git pull --ff-only` on later runs) into
`._temp/openspec/`, via `common/gitsource.py`. Fails fast if
`website/docs.sync.config.mjs` is missing after the clone.

## Ordering & layout (`refresh.py`)
`parse_manifest()` reads the manifest's `docsDir` and `sections` exports with a
small, strict JS-literal parser (`_strip_comments` + `_JSLiteral`). The sidebar
becomes the layout:
- each section → an `NN-<slugified label>` folder (`01-start/`, `04-reference/`),
- each page → `NN-<last slug segment>.md` (`01-start/01-installation.md`),
- each folder entry (`{ folder, label, pages }`, e.g. Reference → Schemas) → a
  nested `NN-<folder>/` directory.

Only **published** pages are mirrored. Entries commented out in the manifest are
held-back drafts (headings-only skeletons) that openspec.dev does not serve.
`docs-lab/`'s maintainer files (`README.md`, `Notes.md`, `sources.md`, …) are
never listed, so they are skipped too.

Page text is verbatim (H1 and `>` description kept, no frontmatter) except for
relative `*.md` links, which are rewritten like upstream's
`website/scripts/sync-docs.mjs` rewrites them, but to the local `NN-` paths
instead of `/docs/...` routes. A link to a page the site doesn't publish falls
back to its GitHub source, as on the site. `docs.sync.config.mjs` is copied to
the docs root as the ordering reference.

The mirror tracks the repo's `main`, which can be slightly **ahead** of the live
site if openspec.dev hasn't redeployed yet.

## Fragile points
- **Manifest syntax vs `_JSLiteral`.** It reads the plain literal style used
  today (objects, arrays, strings, numbers, booleans, comments, trailing commas).
  A spread, variable, function call, or `${}` interpolation inside `sections`
  makes it raise with a line number. Refresh then aborts **before** touching
  `docs/openspec/`, so the last good build survives.
- **Manifest location.** `website/docs.sync.config.mjs` (`SYNC_CONFIG` in
  `fetch.py`/`refresh.py`). `docsDir` itself is read from the manifest, so the
  planned cutover away from `docs-lab/` (see upstream `docs-lab/sources.md`) is
  followed automatically.
- **Missing pages are fatal**, as in upstream's own site build: if the manifest
  lists a file that isn't in the repo, refresh raises and keeps the old build.
- **Diagrams.** sync-docs.mjs also copies `<docsDir>/diagrams/*.png|svg` to the
  site's `/diagrams/`. None exist today, so they aren't mirrored.

## If it breaks
- "docs.sync.config.mjs line N: …" → open `._temp/openspec/website/docs.sync.config.mjs`
  at that line, see what construct appeared, and extend `_JSLiteral`.
- "manifest lists … page(s) not found under …" → upstream's manifest points at a
  file that isn't there (their site build fails too); wait for the upstream fix.
- "expected …/website/docs.sync.config.mjs after clone" → the repo restructured;
  update `SYNC_CONFIG` in `fetch.py` and `refresh.py`.
- "broken link -> …" from verify → a link shape `rewrite_links()` doesn't handle.

## Verify (`verify.py`)
Expects ≥ 15 pages (20 today), `start` and `reference` sections,
`docs.sync.config.mjs` present, no empty/HTML-error pages, and every relative
`.md` link resolving to a mirrored file. Run `wd verify openspec`.
