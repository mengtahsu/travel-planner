# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt   # anthropic, jinja2, requests
pip install ddgs                  # DDG image search (imported as `from ddgs import DDGS`, not in requirements.txt)

# Secrets — provide EITHER a local file (gitignored) OR an env var. File wins if present.
#   anthropic_api_key.txt  | ANTHROPIC_API_KEY  — Claude API key (required)
#   github_token.txt       | GITHUB_TOKEN       — GitHub fine-grained PAT (contents:read/write on repo)
#   serper_api_key.txt     | SERPER_API_KEY     — Serper.dev key for Google image search (optional; falls back to DDG)

# Run manually
python generator.py
# Output logged to logs/generator.log (UTF-8, tee'd from stdout/stderr)

# Generate a placeholder index.html with mock Paris data (no API calls — for first deploy / template work)
python generate_first.py

# Local "regenerate now" server (chat.html's "Run now" button hits http://localhost:8766/run)
python trigger_server.py

# Auto-run chain (Windows Task Scheduler, every 10 min):
#   Task Scheduler → run_generator.vbs (silent, no console)
#     → run_generator.bat (sets UTF-8 encoding, cds to project dir)
#       → python generator.py 2>&1 | Tee-Object logs/generator.log
```

## Architecture

Bilingual (EN/繁體中文) travel itinerary generator. Static GitHub Pages site + Python generator running on user's PC via Windows Task Scheduler (every 10 min).

```
User's PC (Windows Task Scheduler, every 10 min)
  run_generator.vbs → run_generator.bat → generator.py
  ├── Reads: config/settings.json (GitHub API first, local fallback)
  ├── Reads: data/chat/YYYY-MM-DD.txt (GitHub API first, local fallback, 7-day fallback)
  ├── Calls: Anthropic Claude API (claude-sonnet-4-6) + DDG Image Search (ddgs)
  ├── Writes: data/plans/YYYY-MM-DD.json
  ├── Writes: index.html (full plan page with inline CSS/JS)
  ├── Logs: logs/generator.log (UTF-8, tee'd)
  └── Push via GitHub REST API → GitHub Pages serves it

GitHub Repo (mengtahsu/travel-planner)
  ├── index.html              ← generated plan (overwritten each gen)
  ├── chat.html               ← chat notes editor (saves to localStorage + GitHub API)
  ├── settings.html           ← settings form (saves to GitHub API)
  ├── log.html                ← saved plans + run history (JS-rendered from data files)
  ├── config/settings.json    ← user settings (read from GitHub by generator)
  ├── data/chat/              ← chat notes per day (read/write via GitHub API)
  ├── data/plans/             ← plan JSON per day
  ├── data/saved/             ← archived plan HTML files + index.json
  ├── data/save_flag.json     ← checkbox flag: "archive this plan before next regeneration"
  ├── data/runs.json          ← generator run log (last 90 days)
  ├── templates/              ← shared.css, shared.js, plan_template.html
  └── generator.py            ← the main engine
```

> **NOTE:** The site is served from GitHub Pages (and mirrored on Netlify). The generator runs on the
> user's Windows PC and pushes to GitHub via the REST API — there is no server-side build step.

## Key Files

| File | Purpose |
|------|---------|
| `generator.py` | Main engine — reads config/chat, calls AI, fetches DDG photos, renders HTML, pushes to GitHub |
| `templates/plan_template.html` | Jinja2 template for `index.html` — inlines `shared.css` and `shared.js` |
| `templates/shared.css` | All styling: hero slider, cards, timeline, lightbox, mobile responsive |
| `templates/shared.js` | Lightbox (click-to-enlarge, arrow keys, esc), broken image handler, Google Images link guard |
| `chat.html` | Chat editor — one textarea per day, saves to `data/chat/YYYY-MM-DD.txt` via GitHub API + localStorage fallback |
| `settings.html` | Settings form — saves to `config/settings.json` via GitHub API |
| `log.html` | Renders saved plans list + run history from GitHub raw URLs (IIFE, promise chains, HTML escaping) |
| `requirements.txt` | Python deps: `anthropic`, `jinja2`, `requests` (note: `ddgs` also required for image search) |
| `generate_first.py` | One-off: renders `index.html` from hardcoded mock Paris plan via `generator.render_html` — no API/network |
| `trigger_server.py` | Local HTTP server on port 8766 — `GET /run` shells out to `generator.py` for on-demand regeneration (chat.html "Run now") |
| `config/settings.json` | User settings (local fallback when GitHub API unavailable) |
| `netlify.toml` | Netlify deploy config — publishes root, `Cache-Control: no-cache` on all files |
| `run_generator.vbs` | Silent VBS wrapper for Task Scheduler — no console window |
| `run_generator.bat` | Batch launcher — sets `chcp 65001`, PYTHONIOENCODING, cds to project, runs generator, tees to log |

## Data Flow

1. User edits chat in `chat.html` → saves to `data/chat/YYYY-MM-DD.txt` via GitHub API (with localStorage fallback)
2. Generator runs every 10 min:
   a. Loads config from GitHub API (falls back to local `config/settings.json`)
   b. Reads today's chat text from GitHub API → local → 7-day lookback (midnight gap fix)
   c. Compares chat+config hashes with stored plan → detects changes
   d. Checks `data/save_flag.json` — if set, archives current `index.html` to `data/saved/` before overwriting
   e. Syncs saved files with GitHub (removes locally-deleted files, cleans orphans)
   f. Fetches live exchange rates from frankfurter.app
   g. If changed: calls Claude API → generates plan JSON, then `validate_plan()` checks required fields (~30-60s)
   h. Fetches DDG image links for destination landmarks, hotels, restaurants, day-by-day photos
   i. Renders `index.html` via Jinja2 template (inlines shared.css + shared.js)
   j. Pushes all changed files to GitHub via REST API (checks SHA to avoid conflicts)
   k. Logs run to `data/runs.json` (keeps last 90 days)

**Priority:** Chat always overrides Settings.

## Generator Functions

- `load_config()` — Reads settings from GitHub API, falls back to local file
- `get_chat_text(today_key)` — Reads chat from GitHub → local → 7-day lookback
- `has_changes()` — Compares current chat/config hashes with stored hashes; returns `(changed, chat_text, chat_hash, config_hash)`
- `get_exchange_rates()` — Fetches live NTD→foreign rates from frankfurter.app, with hardcoded fallbacks
- `build_prompt(config, chat_text, rates)` — Constructs the full Claude prompt with live exchange rates
- `call_ai(prompt)` — Calls Claude API (`claude-sonnet-4-6`, max_tokens 8192), extracts the first `{...}` JSON block from response
- `validate_plan(plan)` — Asserts required plan fields exist (see `REQUIRED_PLAN_FIELDS`); raises `ValueError` on missing/empty `itinerary`/`hotels`
- `search_images(query, count)` — Photo dispatcher: Serper (Google) primary, DDG fallback, placeholders last; returns `[{url, label}]` (links only). Backends: `_serper_images()` (returns `None` to signal fallback), `_ddg_images()` (never raises); shared `_is_good_photo()`/`_collect()` filter+dedupe
- `resolve_all_photos(plan)` — Resolves photos: cover/hotels/restaurants via `search_images`, day-by-day via `_ddg_images` (hero reuses cover[0])
- `render_html(plan)` — Renders `index.html` from Jinja2 template (with `build_tag` timestamp)
- `push_via_api(today_key)` — Pushes files to GitHub via REST API (PUT with SHA to avoid conflicts)
- `_sync_saved_files()` — Syncs saved HTML files: removes local orphans not in index, cleans up GitHub-deleted files
- `check_and_archive()` — Archives current plan to `data/saved/` when `save_flag.json` is set, then clears the flag
- `log_run()` — Appends run entry to `data/runs.json` (prunes to last 90 days)
- `safe_print()` — Print wrapper that handles UnicodeEncodeError on Windows consoles

## Photo System

- **Primary source:** Serper.dev (real Google Images) for cover, hotels, restaurants — `POST https://google.serper.dev/images` with `X-API-KEY` (key via `serper_api_key.txt` | `SERPER_API_KEY`). Returns direct image URLs (no key in URL, no expiry).
- **DDG (`ddgs`)** is used for day-by-day photos (generic filler, off the Serper quota) **and** as the automatic fallback when `SERPER_API_KEY` is missing or Serper hits quota/error (HTTP 402/429). Functions: `search_images()` (dispatcher) → `_serper_images()` / `_ddg_images()`, sharing `_is_good_photo()`/`_collect()`.
- **Links only** — direct image URLs embedded in HTML, no file downloads
- **Filtering:** Blocks watermarks (alamy, shutterstock, gettyimages, etc.), stock sites, travel booking ads, Pinterest
- **Deduplication** by URL — never show same photo twice
- **Hotel/dining photos** wrapped in `<a>` links to Google Images search
- **Lightbox** skips images inside Google Images links (lets the browser follow the link instead)

## Dining Card Layout

- 2 stacked images on left (vertical, `gap: 4px`, `border-radius: 4px`)
- Single image gets `height: 130px` (via `:only-child`)
- No duplicate images (Jinja2 template checks URL uniqueness with `{% set shown = [] %}`)
- Mobile: text bumped up (h4: 1rem, zh-name: 0.8rem for small phones)
- Each restaurant card links to Google Maps for the address

## Log Page Architecture

- IIFE wrapper, no global scope pollution
- Promise chains (`.then/.catch`), no async/await
- All string concatenation (no template literals — compatibility constraint)
- HTML escaping via `esc()` function for user data
- "Loading..." indicator on start; error messages shown inline for all failure modes
- Delete removes row from DOM immediately + localStorage tracking (don't wait for Pages deploy)
- Fetches from `raw.githubusercontent.com` (not GitHub API — no auth needed for read)

## Test Procedure

**MANDATORY before every push or "done" claim.** Full spec at `docs/superpowers/specs/2026-05-10-travel-planner-design.md`.

9 test sections: Chat, Settings, Saved Pages, Midnight Gap, Photos, API Health, Log Page, Save Checkbox, DDG Image Source.

Key test rules (also in memory):
- No permission prompts during testing — use `dangerouslyDisableSandbox: true`
- No `cd` in commands — use absolute paths
- Clean up temp files after tests
- Re-run full test after any test plan or test code change
- Don't claim "done" without fresh verification evidence
