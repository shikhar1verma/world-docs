# codex — extraction notes

How these docs are extracted and how to fix breakage. Output: `docs/codex/`.

## Source
OpenAI Codex docs at **https://developers.openai.com/codex** (no public docs
repo — OpenAI keeps the canonical docs on the site). HTTP extraction.

## Fetch (`fetch.py`)
1. Download the navigation index `codex/llms.txt` — plain Markdown: `## Section`
   headings, each followed by `- [title](url)` bullets whose URLs point at
   per-page `.md` twins under `/codex/`.
2. Download every page's twin at `https://developers.openai.com/codex/<slug>.md`
   in parallel.
3. Download the whole-file references `llms-full.txt` and `codex-manual.md`.

The `## Section` / `- [t](url)` parsing lives in `common/llms_txt.py`
(`parse_sections`), keyed on the `/codex/` URL marker.

## Ordering & layout (`refresh.py`)
`llms.txt` section order drives the layout: each section becomes an `NN-<section>`
folder and its pages are flattened to their leaf name, `NN-` prefixed:
`docs/codex/<NN-section>/<NN-leaf>.md`. `llms.txt`, `llms-full.txt`, and
`codex-manual.md` are copied to the docs root as references.

## Fragile points
- The **`/codex/` URL marker** (`MARKER` in `fetch.py`/`refresh.py`) — identifies
  which bullet URLs are content pages.
- The **`llms.txt` line shapes** (`## Section`, `- [title](url)`), parsed in
  `common/llms_txt.py`. A format change there breaks *all* llms.txt sources.

## If it breaks
- "0 sections, 0 content pages" → the index format changed. `curl -s
  https://developers.openai.com/codex/llms.txt | head -40` and adjust `MARKER` or
  the regexes in `common/llms_txt.py`.
- Many `HTTP 404` → the `/codex/<slug>.md` twin convention changed.

## Verify (`verify.py`)
Expects ≥ 60 pages, `llms.txt` present, no empty/HTML-error pages (sections are
dynamic, so none are required by name). Run `wd verify codex`.
