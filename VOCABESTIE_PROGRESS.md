# Vocabestie — Progress Tracker v2.0

> **Purpose**: Track development progress across Claude Code sessions
> **Instructions**: Update this file at the END of each coding session

---

## 🚦 Current Status

| Item | Status |
|------|--------|
| **Current Phase** | Phase 5: Authentication ✅ COMPLETE |
| **Last Session** | January 27, 2026 |
| **Next Task** | Phase 6: Polish & Content (2000+ words) |
| **Blockers** | None |

---

## 📋 Phase Checklist

### Phase 1: Foundation & Data ✅ COMPLETE
- [x] Database schema (7 tables)
- [x] Alembic migrations
- [x] Vocabulary data (10 scenarios, 198 words)
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

### Phase 6-7: Future
- [ ] Polish & Content (2000+ words)
- [ ] Launch Prep

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
│   └── static/js/tts.js
├── scripts/seed_data.py
├── data/vocabulary.json
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

---

## 📎 Claude Code Session Starter

```
Read VOCABESTIE_PLAN.md and VOCABESTIE_PROGRESS.md to understand the project.

This is Vocabestie, a Swedish vocabulary learning app with:
- Scenario-based organization (Vocabulary → Scenarios → Words)
- 4-skill mastery system (Read, Listen, Speak, Write)
- Adaptive learning that picks exercises based on user weakness
- Dark theme with Swedish flag colors (blue/yellow)
- Google OAuth authentication with server-side sessions

Current status: Phase 5 complete (Authentication)
Next task: Phase 6 - Polish & Content (2000+ words)
```

---

*Update this file at the end of every Claude Code session!*
