# claude-code — extraction notes

Plain-English guide to how these docs are extracted, and how to fix it when the
upstream changes. Output: `docs/claude-code/`.

## Source
Claude Code docs at **https://code.claude.com/docs** (English, `en`). There is no
public docs repo, so extraction is over HTTP.

## Fetch (`fetch.py`)
1. Download one rendered page — `en/overview` — as HTML.
2. `extract_navigation()` pulls the full navigation tree out of the Next.js
   "flight" payload embedded in that HTML (the object after the escaped
   `\"navigation\":` key, brace-matched, then unicode-unescaped to JSON).
3. Write the English `{language, tabs}` tree to `._temp/claude-code/nav.json`.
4. Download every page in parallel by appending `.md` to its slug:
   `https://code.claude.com/docs/en/<slug>.md`.

## Ordering & layout (`refresh.py`)
`nav.json` defines tabs → groups → pages. Output mirrors that with `NN-` prefixes:
`docs/claude-code/<NN-tab>/<NN-group>/<NN-page>.md`. Pages whose slug has its own
path keep only their leaf name (the tab/group folders supply the hierarchy).
`nav.json` is copied to the docs root as the ordering reference.

## Fragile points
- **`extract_navigation()`** (in `fetch.py`) is the brittle bit. It depends on
  the `\"navigation\":` key and a JSON-in-JS-string encoding. If code.claude.com
  changes how it embeds navigation, this raises `navigation block not found` or
  produces bad JSON.
- The per-page **`<slug>.md` twin URL** pattern. If pages start 404-ing, the
  Markdown-twin convention or the `/en/` language segment changed.

## If it breaks
- `RuntimeError: navigation block not found` → open the seed page HTML
  (`curl -s https://code.claude.com/docs/en/overview | less`), find how the nav
  is now embedded, and update `extract_navigation()`.
- Many `HTTP 404` during download → check `BASE` / `LANG` and the `.md` suffix
  convention in `fetch.py`.

## Verify (`verify.py`)
Expects ≥ 100 pages, a `getting-started` top section, `nav.json` present, and no
empty/HTML-error pages. Run `wd verify claude-code`.
