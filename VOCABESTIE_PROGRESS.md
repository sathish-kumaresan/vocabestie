# Vocabestie — Progress Tracker v2.0

> **Purpose**: Track development progress across Claude Code sessions
> **Instructions**: Update this file at the END of each coding session

---

## 🚦 Current Status

| Item | Status |
|------|--------|
| **Current Phase** | Phase 6.5: Vocabulary Corrections & Reordering (IN PROGRESS) |
| **Last Session** | January 27, 2026 |
| **Next Task** | Finish moving 295 words to correct CEFR levels, reorder all levels by frequency, re-seed DB |
| **Blockers** | None |

---

## 📋 Phase Checklist

### Phase 1: Foundation & Data ✅ COMPLETE
- [x] Database schema (7 tables)
- [x] Alembic migrations
- [x] Vocabulary data (331 CEFR levels, 8,204 words)
- [x] API endpoints for scenarios and words

### Phase 2: Core UI Shell ✅ COMPLETE
- [x] Dark theme with Swedish colors
- [x] Bottom navigation (4 tabs)
- [x] Home, Scenarios, Vocabulary, Settings pages
- [x] TTS pronunciation

### Phase 3: Learning Engine ✅ COMPLETE
- [x] Mastery calculation service (`app/services/mastery.py`)
  - [x] Update mastery after exercise
  - [x] Get word mastery (all 4 skills)
  - [x] Derive word status (not_started, in_progress, mastered)
  - [x] Get weakest skill for adaptive learning
  - [x] Testing mode flag (randomizes skill selection for testing all 4 types)
- [x] Session service (`app/services/session.py`)
  - [x] Adaptive word selection (prioritize low mastery + new words)
  - [x] Generate exercise data per skill type
  - [x] Answer checking
- [x] Learning router (`app/routers/learning.py`)
  - [x] `GET /learn/scenario/{id}` - Start learning session
  - [x] `GET /learn/exercise/{word_id}` - Get exercise
  - [x] `POST /learn/answer` - Submit answer
  - [x] `GET /learn/complete` - Session summary
- [x] Exercise templates (4 skill types)
  - [x] Read exercise (Swedish → pick English)
  - [x] Listen exercise (Audio → pick English)
  - [x] Speak exercise (Speech recognition)
  - [x] Write exercise (Jumbled letters)
- [x] Session flow (progress bar, feedback, completion)
- [x] TTS with native Swedish voice selection (`app/static/js/tts.js`)

### Phase 4: Progress & Stats ✅ COMPLETE
- [x] Streak tracking logic (`app/services/stats.py`)
  - [x] Update streak after practice
  - [x] Track longest streak
  - [x] Daily practice log
- [x] Time tracking per session
  - [x] Track session duration in JavaScript
  - [x] Store in daily_practice_log
  - [x] Display on completion screen
- [x] Statistics page with real data (`/settings`)
  - [x] Words mastered count
  - [x] Current/longest streak
  - [x] Total practice time
  - [x] Exercises completed
  - [x] Overall progress bar
- [x] Word status computation in UI
  - [x] Show status badges (Not started, In Progress, Mastered, Known)
  - [x] Show progress percentage per word
- [x] Progress percentages per scenario
  - [x] Scenarios list with progress bars
  - [x] Scenario detail with breakdown (mastered/in progress/not started)
  - [x] Home page overall progress
- [x] "Already known" marking feature
  - [x] API endpoint `POST /api/words/{id}/known`
  - [x] Toggle buttons on scenario detail page
  - [x] Toggle buttons on vocabulary page
  - [x] Filter by status on vocabulary page

### Phase 5: Authentication ✅ COMPLETE
- [x] Google OAuth integration (`app/routers/auth.py`)
  - [x] Login flow (`GET /auth/login/google`)
  - [x] OAuth callback (`GET /auth/callback/google`)
  - [x] Logout (`POST /auth/logout`)
- [x] Server-side sessions (`app/models/session.py`, `app/services/auth.py`)
  - [x] 30-day session duration
  - [x] Secure HttpOnly cookies
  - [x] Session table with Alembic migration
- [x] User identification (`app/dependencies.py`)
  - [x] `get_current_user()` dependency
  - [x] `get_user_id()` dependency
  - [x] `get_auth_context()` for templates
- [x] Guest data migration on first login
  - [x] Transfer all progress data from guest (user_id=1) to new user
- [x] UI updates
  - [x] Header with auth status (`base.html`)
  - [x] Profile section with sign in/out (`settings.html`)
- [x] Config updates (`app/config.py`)
  - [x] OAuth credentials loaded from `oauth.json`
  - [x] Session middleware added

### Phase 6: Vocabulary Import & PWA ✅ COMPLETE
- [x] Import script structure (`scripts/import_vocabulary/`)
  - [x] `fetch_words.py` - Download and filter source words
  - [x] `generate_data.py` - AI batch processing with Claude
  - [x] `merge_data.py` - Combine batches into vocabulary.json
  - [x] `run_import.py` - Main orchestrator
- [x] Scenarios master file (`data/import/scenarios_master.json`)
  - [x] 42 scenarios defined (26 new + 10 existing + 6 grammar)
- [x] Fetched and filtered words
  - [x] Source: 10,000 Swedish words (frequency-sorted)
  - [x] Filtered: 8,012 words
  - [x] Saved to `data/import/filtered_words.json`
- [x] AI generation with Claude
  - [x] Ran `generate_data.py` — 161 batches processed
  - [x] Generated vocabulary for 42 scenarios, 8,204 total words
  - [x] Merged into `data/vocabulary.json`
- [x] Updated `scripts/seed_data.py` to clear mastery/status data on re-seed
- [x] Re-seed database with new vocabulary (`python scripts/seed_data.py --clear`)
- [x] Redistribute vocabulary into CEFR levels
  - [x] `scripts/redistribute_vocabulary.py` — pools all words, groups by A1-C2, splits into ~25-word chunks
  - [x] 331 level groups: A1 (56), A2 (55), B1 (57), B2 (54), C1 (55), C2 (54)
  - [x] Re-seeded database with 331 levels, 8,204 words
- [x] Rename UI from "Scenarios" to "Levels"
  - [x] `base.html` — nav label and meta description
  - [x] `scenarios.html` — page title, heading, subtitle, empty state
  - [x] `scenario_detail.html` — "Words in this level"
  - [x] `learning/complete.html` — "Level progress", "Choose Another Level"
  - [x] `learning/no_words.html` — level references
- [x] Basic PWA setup
  - [x] `app/static/manifest.json` — app name, display standalone, Swedish colors
  - [x] `app/static/icons/` — PNG icons (192, 512) + screenshots (wide, narrow)
  - [x] `app/static/sw.js` — service worker (cache-first static, network-first HTML/API)
  - [x] `app/templates/base.html` — manifest link, theme-color, mobile meta tags, SW registration

### Phase 7: Launch Prep (Future)
- [ ] Landing page
- [ ] Privacy policy, terms of service
- [ ] Deployment setup

---

## 📁 Current Codebase Structure

```
vocabestie/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py          # Auth dependencies (get_user_id, get_current_user)
│   ├── models/
│   │   ├── user.py, scenario.py, word.py, mastery.py, session.py
│   ├── schemas/
│   │   ├── scenario.py, word.py
│   ├── routers/
│   │   ├── scenarios.py, words.py, learning.py, auth.py
│   ├── services/
│   │   ├── mastery.py, session.py, stats.py, auth.py
│   ├── templates/
│   │   ├── base.html, home.html, scenarios.html
│   │   ├── scenario_detail.html, vocabulary.html, settings.html
│   │   └── learning/
│   │       ├── session.html, complete.html, no_words.html
│   │       ├── exercise_read.html, exercise_listen.html
│   │       ├── exercise_speak.html, exercise_write.html
│   └── static/
│       ├── js/tts.js
│       ├── manifest.json            # PWA manifest
│       ├── sw.js                    # Service worker
│       └── icons/                   # PWA icons & screenshots
├── scripts/
│   ├── seed_data.py
│   └── redistribute_vocabulary.py  # CEFR level redistribution
├── data/
│   └── vocabulary.json
├── oauth.json                   # Google OAuth credentials (not in git)
├── alembic/
└── docker-compose.yml
```

---

## 🔧 Quick Commands

```bash
cd ~/projects/vocabestie
docker compose up -d
source ~/venv/bin/activate
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload
```

---

## 📊 Session Log

| Date | What Was Done |
|------|---------------|
| Jan 26, 2026 | Phase 1: Database schema, migrations, seed data, API |
| Jan 26, 2026 | Phase 2: Dark theme UI, navigation, all pages |
| Jan 26, 2026 | Phase 3: Learning engine with 4-skill exercises |
| Jan 26, 2026 | Phase 3 fixes: TTS native Swedish voice selection, exercise template improvements, testing mode for skill randomization |
| Jan 26, 2026 | Phase 4: Streak tracking, time tracking, statistics page, word status UI, scenario progress, "already known" feature |
| Jan 27, 2026 | Phase 5: Google OAuth authentication, server-side sessions, guest data migration, auth UI |
| Jan 27, 2026 | Phase 6 started: Vocabulary import scripts, 42 scenarios defined, 9,806 words fetched and filtered |
| Jan 27, 2026 | AI vocabulary generation: 161 batches via Claude API, 8,204 words across 42 scenarios. Updated seed script, fetch_words, generate_data scripts. Basic PWA setup: manifest.json, PNG icons (192/512), screenshots (wide/narrow), service worker (cache-first static, network-first HTML/API), base.html meta tags and SW registration |
| Jan 27, 2026 | Redistributed vocabulary into CEFR levels (A1-C2) with ~25 words per group (331 levels total). Created `scripts/redistribute_vocabulary.py`. Re-seeded database. Renamed all UI references from "Scenarios" to "Levels" across 5 templates. Phase 6 complete. |
| Jan 27, 2026 | Performance Optimization: Fixed slow "Vocabulary" page by implementing server-side pagination, search, and bulk status fetching. Reduced N+1 queries. |
| Jan 27, 2026 | Levels Refactor: Grouped 331 levels into 6 CEFR categories (A1-C2) to fix "Levels" page performance. Added aggregated progress stats and drill-down pages. |
| Jan 27, 2026 | Route Update: Changed main route from `/scenarios` to `/levels` to reflect the new hierarchy. Updated all template links and navigation. |
| Jan 27, 2026 | **Major Refactor**: Flattened vocabulary structure. Removed sub-scenarios entirely. merged all words into single "Level A1", "Level A2", etc. lists (~1300 words each). |
| Jan 27, 2026 | **Pagination**: Implemented server-side pagination for level word lists to handle large datasets. Added word limit selector (25/50/100) and page navigation controls. |
| Jan 27, 2026 | **Git Push**: Pushed all recent changes (Flattening + Pagination) to the remote repository. |
| Jan 27, 2026 | **Global Sorting**: Implemented a global sort for all CEFR levels based on word length + Swedish alphabetical order (i.e. shortest words first). Replaced previous frequency/category logic. Updated `reorder_vocab.py` with custom Swedish sort key (`åäö` > `z`). Verified DB: A1 starts with `i, å, ö...`. |

---

## 📎 Claude Code Session Starter

```
Read VOCABESTIE_PLAN.md and VOCABESTIE_PROGRESS.md to understand the project.

This is Vocabestie, a Swedish vocabulary learning app with:
- CEFR level-based organization (Levels → Words, grouped A1-C2)
- 4-skill mastery system (Read, Listen, Speak, Write)
- Adaptive learning that picks exercises based on user weakness
- Dark theme with Swedish flag colors (blue/yellow)
- Google OAuth authentication with server-side sessions

Current status: Phase 6 complete (Vocabulary Import, CEFR Levels, PWA)
Next task: Phase 7 — Launch Prep (landing page, privacy policy, deployment)
```

---

*Update this file at the end of every Claude Code session!*
