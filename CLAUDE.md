# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static homepage (no build step, no server-side dependencies) for マジックタンノ (Magic Tanno), a Japanese doujin circle that publishes technical books at events like 技術書典 (Tech Book Fest), コミケ (Comiket), and 技書博. There is no test suite or linter.

`index.html` now renders its 年表 (timeline) / 構成員 (members) / 頒布物 (works) sections dynamically at load time via `js/data-loader.js`, which `fetch()`s `data/*.json`. Because `fetch()` of local files is blocked by CORS under `file://`, **`index.html` cannot be opened by double-clicking it** — preview it via a local static server from the repo root, e.g. `npx serve .` or `npx http-server .`, then open the printed `http://localhost:...` URL. On the deployed site (served over http/https, e.g. GitHub Pages) this is a non-issue.

## Current state (branch: `refactor/index`)

- `data/members.json`, `data/timeline.json`, `data/works.json` — the single source of truth for content. Every entry in all three files has a stable `id` slug (used as a GUI/DOM key; not referenced across files).
- `js/data-loader.js` — fetches the three JSON files on `DOMContentLoaded` and renders them into `#members-list`, `#timeline-list`, `#works-list` in `index.html`. On fetch failure (e.g. opened via `file://`) it shows an inline error message instead of a blank page.
- `css/` — still empty; no styling has been added back yet. Out of scope unless explicitly asked.
- `tools/` — a small Python + Tkinter GUI (managed via `uv`, no extra dependencies) for editing the three `data/*.json` files without hand-editing JSON. Run it with `uv run python main.py` from `tools/`. `uv run python -c "import tkinter; tkinter.Tk()"` is the sanity check if tkinter ever fails to import (this machine has no standalone Python install — `uv` provisions its own via `uv python install`).
- **Exception**: the "Air-LiDAR（タンノのエアライダー）" project-exhibit entry inside `#works-list` in `index.html` is intentionally hardcoded, not in `works.json` — it's a hardware demo, not a 頒布物 (published work), so `js/data-loader.js` appends JSON-driven entries alongside it rather than clearing the container.

`index.html`'s previous malformed structure (a premature `</body></html>` mid-file, a stray unmatched `</div>`) has been fixed — it's now a single well-formed document.

## Content model

- **members**: `id`, `name`, `roles` (array of tag strings), `description`, `contacts` (array of `{type, label, value, url}` — `type` is free text, not an enum).
- **timeline**: `id`, `datetime` (ISO date, used for the `<time datetime>` attribute), `displayDate` (Japanese-formatted date string, not auto-derived from `datetime`), `title`, `description`. Ordered chronologically.
- **works**: `id`, `type` (free text, e.g. 新刊/既刊/既刊（電子）), `event` (empty string `""` if none), `author` (free text — an author name, co-author list, or series/volume label; semantics vary by entry but display is uniform), `title`, `description`, `url` (empty string `""` if none). Note some URLs are still placeholders (e.g. `example.booth.pm`, `techbookfest.org/product/example`) — don't treat these as real links.

All content is Japanese; preserve full-width punctuation and existing terminology (circle/member names, event names like 技術書典/コミケ/技書博) exactly as written rather than normalizing them.
