# Vocabestie — Progress Tracker v2.0

> **Purpose**: Track development progress across Claude Code sessions  
> **Instructions**: Update this file at the END of each coding session

---

## 🚦 Current Status

| Item | Status |
|------|--------|
| **Current Phase** | Phase 1: Foundation & Data |
| **Last Session** | January 26, 2026 |
| **Next Task** | Delete old Phase 1 code, set up new database schema |
| **Blockers** | None |

---

## 📋 Phase 1 Checklist: Foundation & Data

### Database Setup
- [ ] Delete old Phase 1 code (keep docker-compose.yml, requirements.txt as reference)
- [ ] Create new database schema (see VOCABESTIE_PLAN.md for SQL)
- [ ] Create Alembic migrations for:
  - [ ] `users` table
  - [ ] `scenarios` table
  - [ ] `words` table
  - [ ] `word_skill_mastery` table
  - [ ] `user_word_status` table
  - [ ] `user_stats` table
  - [ ] `daily_practice_log` table
- [ ] Test migrations (up and down)

### Vocabulary Data
- [ ] Research Swedish vocabulary sources:
  - [ ] Språkbanken frequency lists
  - [ ] Wiktionary Swedish-English
  - [ ] Tatoeba example sentences
  - [ ] CEFR word lists
- [ ] Create data import script structure
- [ ] Define JSON format for vocabulary data
- [ ] Import first 10 scenarios (~500 words):
  - [ ] 🏠 At Home
  - [ ] 🏢 At the Office
  - [ ] 🛒 Shopping
  - [ ] 🍽️ Restaurant & Café
  - [ ] 🏥 At the Doctor
  - [ ] ✈️ At the Airport
  - [ ] 👤 Pronouns
  - [ ] 🔢 Numbers
  - [ ] 🎨 Colors
  - [ ] ❓ Question Words

### API Endpoints
- [ ] `GET /api/scenarios` — List all scenarios with progress
- [ ] `GET /api/scenarios/{id}` — Scenario detail with words
- [ ] `GET /api/words` — List/search words with filters
- [ ] `GET /api/words/{id}` — Word detail with skill mastery

---

## 🔜 Upcoming Phases Summary

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Foundation & Data | 🔄 In Progress |
| Phase 2 | Core UI Shell | ⏳ Waiting |
| Phase 3 | Learning Engine | ⏳ Waiting |
| Phase 4 | Progress & Stats | ⏳ Waiting |
| Phase 5 | Authentication | ⏳ Waiting |
| Phase 6 | Polish & Content | ⏳ Waiting |
| Phase 7 | Launch Prep | ⏳ Waiting |

---

## 📁 Current Codebase Status

### Files to DELETE (Old Phase 1)
```
app/
├── models/word.py          # DELETE - old schema
├── schemas/word.py         # DELETE - old schema  
├── routers/words.py        # DELETE - old implementation
├── routers/flashcards.py   # DELETE - old implementation
├── routers/quiz.py         # DELETE - old implementation
├── services/spaced_repetition.py  # KEEP for reference, rename
├── templates/*.html        # DELETE - old light theme
```

### Files to CREATE (New Phase 1)
```
app/
├── models/
│   ├── __init__.py
│   ├── user.py             # NEW
│   ├── scenario.py         # NEW
│   ├── word.py             # NEW (different schema)
│   └── mastery.py          # NEW
├── schemas/
│   ├── __init__.py
│   ├── user.py             # NEW
│   ├── scenario.py         # NEW
│   ├── word.py             # NEW
│   └── session.py          # NEW
├── routers/
│   ├── __init__.py
│   ├── scenarios.py        # NEW
│   └── words.py            # NEW
├── services/
│   ├── __init__.py
│   └── mastery.py          # NEW (4-skill system)
scripts/
├── import_vocabulary.py    # NEW
data/
└── swedish_vocabulary.json # NEW
```

---

## 🔧 Environment Notes

- **PostgreSQL**: Running via Docker on port **5433** (not 5432)
- **Python venv**: `/home/sathish/venv/`
- **Project path**: `~/projects/vocabestie/`
- **GitHub repo**: `sathish-kumaresan/vocabestie`

### Quick Commands

```bash
# Navigate to project
cd ~/projects/vocabestie

# Start database
docker compose up -d

# Activate venv
source ~/venv/bin/activate

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload

# Check database
docker compose ps
```

---

## 📊 Session Log

| Date | Duration | What Was Done | Commits |
|------|----------|---------------|---------|
| Jan 26, 2026 | Planning | Complete product redesign based on WRD analysis | Plan v2.0 |

---

## 💡 Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Keep backend framework | FastAPI + PostgreSQL | Solid foundation, no need to change |
| Rebuild frontend | Complete redesign | WRD-style dark theme, new tab structure |
| New data model | Scenario → Word → 4 Skills | Better pedagogy than old flashcard model |
| No user-added words v1 | Excluded | Focus on quality curated content first |
| Swedish colors | Blue #006AA7 + Yellow #FECC00 | Unique identity, not WRD clone |
| 4 tabs | Home, Scenarios, Vocabulary, Settings | Clean navigation matching app structure |
| Adaptive learning | Fully adaptive | System picks skill based on mastery + time |

---

## 🐛 Known Issues

*None yet — fresh start!*

---

## 💭 Ideas & Parking Lot

*Features for future versions (post-v1)*

- User-added custom words
- Reverse direction testing (English → Swedish)
- Images for words (AI-generated)
- Offline mode with sync
- Social features (share progress)
- Multiple language support
- Spaced repetition visualization

---

## 📎 Claude Code Session Starter

Copy and paste this when starting a new Claude Code session:

```
Read VOCABESTIE_PLAN.md and VOCABESTIE_PROGRESS.md to understand the project.

This is Vocabestie, a Swedish vocabulary learning app with:
- Scenario-based organization (Vocabulary → Scenarios → Words)
- 4-skill mastery system (Read, Listen, Speak, Write)
- Adaptive learning that picks exercises based on user weakness
- Dark theme with Swedish flag colors (blue/yellow)
- No gamification gimmicks (no gems, no forced daily plans)

Current status: Phase 1 - Foundation & Data
Next task: [Check the progress file for current next task]

Let's continue from where we left off.
```

---

*Update this file at the end of every Claude Code session!*
