# openai-api — extraction notes

How these docs are extracted and how to fix breakage. Output: `docs/openai-api/`.

## Source
OpenAI API docs at **https://developers.openai.com/api** (no public docs repo).
HTTP extraction — same shape as `codex`, against the `/api/` base.

## Fetch (`fetch.py`)
1. Download the index `api/llms.txt` — `## Section` headings (Docs, Reference)
   with `- [title](url)` bullets pointing at per-page `.md` twins under `/api/`.
2. Download every page's twin at `https://developers.openai.com/api/<slug>.md`
   in parallel. Slugs are deep, e.g.
   `reference/resources/audio/subresources/speech/methods/create`.
3. Download the whole-file reference `llms-full.txt`.

Parsing is shared (`common/llms_txt.py`, `parse_sections`) keyed on the `/api/`
URL marker.

## Ordering & layout (`refresh.py`)
The index has only two content sections but the real hierarchy is encoded inside
each slug (up to ~11 levels), and leaf names collide heavily (dozens of
create/list/delete). So we do **not** flatten: the two sections become
`01-docs/` and `02-reference/`, and the **full slug path is mirrored verbatim**
inside (dropping the redundant leading `docs/`|`reference/` segment the folder
already carries). `llms.txt` and `llms-full.txt` are copied to the docs root.

## Fragile points
- The **`/api/` URL marker** (`MARKER` in `fetch.py`/`refresh.py`).
- The **`llms.txt` line shapes**, parsed in `common/llms_txt.py` (shared with
  `codex` — a change there affects both).

## If it breaks
- "0 sections, 0 content pages" → `curl -s
  https://developers.openai.com/api/llms.txt | head -40` and adjust `MARKER` or
  the regexes in `common/llms_txt.py`.
- Many `HTTP 404` → the `/api/<slug>.md` twin convention changed.

## Verify (`verify.py`)
Expects ≥ 250 pages, `docs` and `reference` top sections, `llms.txt` present, no
empty/HTML-error pages. Run `wd verify openai-api`.
