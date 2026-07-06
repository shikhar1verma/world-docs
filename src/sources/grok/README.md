# grok — extraction notes

How these docs are extracted and how to fix breakage. Output: `docs/grok/`.

## Source
Grok / xAI docs at **https://docs.x.ai** (no public docs repo). HTTP extraction.

## Fetch (`fetch.py`)
Unlike the OpenAI/Codex indexes, Grok's `llms.txt` is a single ~1.2 MB
**concatenated export**: every page's Markdown inlined, delimited by
`===/<slug>===` marker lines. So the whole corpus arrives in one download:
1. Download `https://docs.x.ai/llms.txt` verbatim to `._temp/grok/llms.txt`.
2. Split it on the `===/<slug>===` markers into `._temp/grok/pages/<slug>.md`
   (splitting locally keeps pages byte-identical to the export and avoids ~140
   extra requests). The split lives in `common/llms_txt.py` (`split_markers`).

## Ordering & layout (`refresh.py`)
Page order is the marker order in the file. Grok slugs are deeply hierarchical
and their leaf names collide across sections, so we do **not** flatten: top-level
sections become `NN-<section>` folders (numbered by first appearance) and the
rest of each slug path is mirrored verbatim inside. A bare section-root slug
(e.g. `overview`) lands as `NN-<section>/<section>.md`. `llms.txt` is copied to
the docs root as the full-export reference.

## Fragile points
- The **`===/<slug>===` marker format** (`_MARKER_RE` in `common/llms_txt.py`).
  If xAI changes the delimiter, the split yields 0 pages.

## If it breaks
- "no pages parsed — marker format may have changed" → `curl -s
  https://docs.x.ai/llms.txt | head -30`, see the new delimiter, and update
  `_MARKER_RE` in `common/llms_txt.py`.

## Verify (`verify.py`)
Expects ≥ 90 pages, `overview` and `developers` top sections, `llms.txt` present,
no empty/HTML-error pages. Run `wd verify grok`.
