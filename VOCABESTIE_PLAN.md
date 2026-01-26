# Vocabestie — Product Plan v2.0

> **Last Updated**: January 26, 2026  
> **Status**: Ready for Development  
> **Version**: Complete Redesign based on WRD analysis + Custom Vision

---

## 🎯 Product Vision

**Tagline**: *Learn Swedish vocabulary your way — scenario-based, skill-driven, no gimmicks.*

**Target Users**: English speakers learning Swedish

**Core Philosophy**:
- **Vocabulary-first**: Organized as Vocabulary → Scenarios → Words
- **4-skill mastery**: Every word tested across Read, Listen, Speak, Write
- **Contextual learning**: Words grouped by realistic situations, not isolated lists
- **User control**: No forced daily plans — user picks where to start
- **Simplicity**: Single status per word, smart system handles complexity
- **Fair model**: No gems, no aggressive paywalls, no currency systems

**Success Metric**: User feels real progress toward Swedish comprehension in 5-10 minute sessions

---

## 🎨 Design System

### Color Palette (Swedish-inspired)
```
Background:       #000000 (pure black)
Card Background:  #1a1a1a (dark grey)
Primary Accent:   #006AA7 (Swedish blue)
Secondary Accent: #FECC00 (Swedish yellow)
Success:          #4CAF50 (green)
Error:            #FF5252 (red)
Text Primary:     #FFFFFF
Text Secondary:   #888888
```

### Typography
- Headers: Bold, clean sans-serif
- Body: Regular weight, high readability
- Swedish words: Slightly larger, prominent

### UI Style
- Dark theme throughout
- Rounded corners (12-16px radius)
- Subtle shadows on cards
- Mobile-first responsive design

---

## 📱 App Structure

### Navigation (4 Tabs)
```
┌─────────┬────────────┬─────────────┬──────────┐
│  Home   │  Scenarios │  Vocabulary │ Settings │
│   🏠    │     📚     │      🔤     │    ⚙️    │
└─────────┴────────────┴─────────────┴──────────┘
```

### Tab Details

#### 1. Home Tab 🏠
- **Streak display**: "🔥 5 days" (motivational)
- **Quick stats**: Words mastered today, time spent
- **Continue Learning**: Button to resume last scenario (if any)
- **Overall progress**: "40% of Swedish vocabulary mastered"
- **Search bar**: Quick search across all words

#### 2. Scenarios Tab 📚
- **List view**: Icon + Scenario name + Progress % + Word count
- **Example rows**:
  ```
  🏢 At the Office          45%    32 words
  🏥 At the Doctor          20%    28 words
  🛒 Shopping               0%     35 words
  ✈️ Travel & Transport     65%    40 words
  ```
- **Tap scenario** → Opens scenario detail with word list
- **"Learn" button** → Starts adaptive learning session

#### 3. Vocabulary Tab 🔤
- **Search bar** at top
- **Filter tabs**: All | Not Started | In Progress | Mastered | Already Known
- **Word list**: Swedish word + English + Status chip + Audio icon
- **Tap word** → Word detail modal (definition, example sentence, skill breakdown)
- **"Already known" option** in word detail

#### 4. Settings Tab ⚙️
- **Profile**: Name, email, sign-in method
- **Statistics**: Detailed stats page
- **Learning Settings**: Session preferences
- **General**: Sound, notifications
- **About**: Version, support, privacy

---

## 📊 Data Model

### Core Entities

```
┌─────────────────────────────────────────────────────────────┐
│                        VOCABULARY                            │
│  (The complete Swedish word collection - 2000+ words)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        SCENARIOS                             │
│  id, name, icon, description, category, word_count          │
│  Examples: "At the Office", "At the Doctor", "Shopping"     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          WORDS                               │
│  id, scenario_id, swedish, english, example_sentence,       │
│  grammar_hint, audio_url, difficulty_level (A1-C2)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     WORD_SKILL_MASTERY                       │
│  id, user_id, word_id, skill_type, mastery_score,          │
│  last_practiced, practice_count, correct_count              │
│                                                              │
│  skill_type: 'read' | 'listen' | 'speak' | 'write'         │
│  mastery_score: 0.0 - 1.0 (threshold: 0.8 = passed)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   WORD_STATUS (Computed)                     │
│                                                              │
│  Status derived from skill mastery:                         │
│  • "Not started" - no skill exercises completed             │
│  • "In progress" - at least one skill below 0.8            │
│  • "Mastered" - all four skills ≥ 0.8 threshold            │
│  • "Already known" - manually set by user                   │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema (PostgreSQL)

```sql
-- Scenarios table
CREATE TABLE scenarios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    icon VARCHAR(10),  -- emoji
    description TEXT,
    category VARCHAR(50),  -- "Daily Life", "Work", "Travel", etc.
    difficulty_level VARCHAR(5),  -- A1, A2, B1, B2, C1, C2
    word_count INTEGER DEFAULT 0,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Words table
CREATE TABLE words (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenarios(id),
    swedish VARCHAR(200) NOT NULL,
    english VARCHAR(200) NOT NULL,
    example_sentence_sv TEXT,
    example_sentence_en TEXT,
    grammar_hint VARCHAR(100),  -- "en-word", "ett-word", "verb", etc.
    pronunciation_url VARCHAR(500),
    difficulty_level VARCHAR(5),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User word skill mastery (per user, per word, per skill)
CREATE TABLE word_skill_mastery (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    word_id INTEGER REFERENCES words(id),
    skill_type VARCHAR(10) NOT NULL,  -- 'read', 'listen', 'speak', 'write'
    mastery_score FLOAT DEFAULT 0.0,  -- 0.0 to 1.0
    last_practiced TIMESTAMP,
    practice_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, word_id, skill_type)
);

-- User word status (for "Already known" manual override)
CREATE TABLE user_word_status (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    word_id INTEGER REFERENCES words(id),
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'already_known'
    marked_at TIMESTAMP,
    UNIQUE(user_id, word_id)
);

-- User stats
CREATE TABLE user_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_practice_date DATE,
    total_practice_time_seconds INTEGER DEFAULT 0,
    total_words_mastered INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Daily practice log (for streak and time tracking)
CREATE TABLE daily_practice_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    practice_date DATE NOT NULL,
    practice_time_seconds INTEGER DEFAULT 0,
    words_practiced INTEGER DEFAULT 0,
    exercises_completed INTEGER DEFAULT 0,
    UNIQUE(user_id, practice_date)
);

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(100),
    auth_provider VARCHAR(20),  -- 'google', 'apple', 'email'
    auth_provider_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

---

## 🎓 Learning System

### The 4-Skill Model

| Skill | Exercise Type | User Action |
|-------|---------------|-------------|
| **Read** | Show Swedish word → 4 English options | Tap correct translation |
| **Listen** | Play Swedish audio → 4 English options | Tap what they heard |
| **Speak** | Show Swedish word → Record pronunciation | Speak into mic, get accuracy % |
| **Write** | Show English word → Jumbled Swedish letters | Arrange letters correctly |

### Mastery Calculation

```python
# Per-skill mastery update (after each exercise)
def update_mastery(current_score, is_correct, time_decay_factor):
    if is_correct:
        # Increase mastery, weighted by recency
        new_score = current_score + (1 - current_score) * 0.3
    else:
        # Decrease mastery
        new_score = current_score * 0.7
    
    # Apply time decay (mastery decreases over time without practice)
    new_score = new_score * time_decay_factor
    
    return min(1.0, max(0.0, new_score))

# Word status derivation
def get_word_status(skill_scores, is_already_known):
    if is_already_known:
        return "Already known"
    
    if all(score == 0 for score in skill_scores.values()):
        return "Not started"
    
    PASS_THRESHOLD = 0.8
    if all(score >= PASS_THRESHOLD for score in skill_scores.values()):
        return "Mastered"
    
    return "In progress"
```

### Adaptive Session Flow

When user taps "Learn" on a scenario:

1. **System selects words** based on:
   - Words due for review (time decay)
   - Words with lowest mastery scores
   - A few new words (not started)
   - Cap at ~10-15 words per session

2. **For each word, system picks skill** based on:
   - Lowest mastery skill gets priority
   - If all skills similar, follow read → listen → speak → write
   - Spaced repetition: recently practiced skills deprioritized

3. **Session continues** until:
   - All selected words practiced across needed skills
   - User manually exits
   - ~10-15 minute natural endpoint

4. **On mistake**:
   - Show correct answer immediately
   - Word queued for repeat later in session

5. **Session end**:
   - Summary screen: words practiced, accuracy, streak update
   - "Continue" or "Done" buttons

---

## 📦 Content: Swedish Vocabulary

### Data Sources (Open, Reliable)
- **Språkbanken** (University of Gothenburg) — Swedish frequency lists
- **Wiktionary** — Definitions, translations, IPA
- **Tatoeba** — Example sentences
- **CEFR Swedish word lists** — A1-C2 level classification
- **Lexin** (Swedish Institute) — Learner dictionary

### Scenario Categories (~50 scenarios, 2000+ words)

```
📁 Daily Life
   ├── 🏠 At Home (35 words)
   ├── 👨‍👩‍👧 Family & Relationships (40 words)
   ├── 🍳 Food & Cooking (45 words)
   ├── 👕 Clothing (30 words)
   ├── 🛒 Shopping (35 words)
   └── ⏰ Daily Routines (30 words)

📁 Work & Education
   ├── 🏢 At the Office (32 words)
   ├── 💼 Job Interview (25 words)
   ├── 📧 Emails & Communication (28 words)
   ├── 🎓 At School/University (35 words)
   └── 💻 Technology (30 words)

📁 Health & Wellbeing
   ├── 🏥 At the Doctor (28 words)
   ├── 💊 Pharmacy (20 words)
   ├── 🏋️ Fitness & Sports (35 words)
   └── 😊 Emotions & Feelings (40 words)

📁 Travel & Transport
   ├── ✈️ At the Airport (30 words)
   ├── 🚂 Public Transport (25 words)
   ├── 🏨 Hotel (25 words)
   ├── 🗺️ Directions (20 words)
   └── 🚗 Driving (25 words)

📁 Social & Leisure
   ├── 🍽️ Restaurant & Café (35 words)
   ├── 🎉 Celebrations (25 words)
   ├── 🎬 Entertainment (30 words)
   ├── ⚽ Hobbies (35 words)
   └── 💬 Small Talk (30 words)

📁 Services & Admin
   ├── 🏦 Banking (25 words)
   ├── 📮 Post Office (15 words)
   ├── 🏛️ Government & ID (20 words)
   └── 📱 Phone & Internet (20 words)

📁 Nature & Weather
   ├── 🌤️ Weather (25 words)
   ├── 🌳 Nature & Outdoors (35 words)
   ├── 🐕 Animals (30 words)
   └── 🌸 Seasons (20 words)

📁 Grammar Essentials
   ├── 👤 Pronouns (25 words)
   ├── 🔢 Numbers (30 words)
   ├── 📅 Days & Months (20 words)
   ├── 🎨 Colors (15 words)
   ├── ❓ Question Words (15 words)
   └── 🔗 Common Verbs (50 words)

📁 Swedish Culture
   ├── 🇸🇪 Traditions (25 words)
   ├── 🎄 Holidays (20 words)
   └── ☕ Fika Culture (15 words)
```

### Word Data Format

```json
{
  "swedish": "möte",
  "english": "meeting",
  "example_sentence_sv": "Jag har ett möte klockan tre.",
  "example_sentence_en": "I have a meeting at three o'clock.",
  "grammar_hint": "ett-word",
  "difficulty_level": "A2",
  "pronunciation_ipa": "/ˈmøːtə/"
}
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL 16 (Docker) |
| **ORM** | SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Frontend** | Jinja2 + HTMX + Tailwind CSS |
| **TTS** | Web Speech API (browser) — Swedish voice (sv-SE) |
| **Speech Recognition** | Web Speech API (browser) |
| **Auth** | Google OAuth, Apple Sign-In, Email/Password |
| **Deployment** | TBD (Railway, Fly.io, or VPS) |
| **Mobile** | PWA first, native shell later |

---

## 📁 Project Structure

```
vocabestie/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings
│   ├── database.py             # SQLAlchemy setup
│   │
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── scenario.py
│   │   ├── word.py
│   │   └── mastery.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── scenario.py
│   │   ├── word.py
│   │   └── session.py
│   │
│   ├── routers/                # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── scenarios.py
│   │   ├── words.py
│   │   ├── learning.py
│   │   ├── stats.py
│   │   └── settings.py
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── mastery.py          # Mastery calculation
│   │   ├── session.py          # Adaptive session logic
│   │   ├── speech.py           # TTS/STT helpers
│   │   └── stats.py            # Statistics calculations
│   │
│   ├── templates/              # Jinja2 templates
│   │   ├── base.html
│   │   ├── components/
│   │   │   ├── nav.html
│   │   │   ├── scenario_card.html
│   │   │   ├── word_item.html
│   │   │   ├── exercise_read.html
│   │   │   ├── exercise_listen.html
│   │   │   ├── exercise_speak.html
│   │   │   └── exercise_write.html
│   │   ├── home.html
│   │   ├── scenarios.html
│   │   ├── scenario_detail.html
│   │   ├── vocabulary.html
│   │   ├── word_detail.html
│   │   ├── learning_session.html
│   │   ├── session_complete.html
│   │   ├── settings.html
│   │   └── statistics.html
│   │
│   └── static/
│       ├── css/
│       │   └── app.css         # Custom styles + Tailwind
│       └── js/
│           ├── app.js          # Main JS
│           ├── speech.js       # TTS/STT
│           └── exercises.js    # Exercise interactions
│
├── scripts/
│   ├── seed_scenarios.py       # Seed scenario data
│   ├── seed_words.py           # Seed word data
│   └── import_vocabulary.py    # Import from sources
│
├── data/
│   └── swedish_vocabulary.json # Master vocabulary file
│
├── alembic/                    # Migrations
├── tests/
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── VOCABESTIE_PLAN.md          # This file
└── VOCABESTIE_PROGRESS.md      # Progress tracker
```

---

## 🗺 Development Phases

### Phase 1: Foundation & Data (Week 1) ✅ COMPLETE
- [x] Set up new database schema (scenarios, words, mastery tables)
- [x] Create Alembic migrations
- [x] Build vocabulary data import script
- [x] Import ~500 words across 10 core scenarios
- [x] Basic API endpoints for scenarios and words

### Phase 2: Core UI Shell (Week 2) ✅ COMPLETE
- [x] Dark theme base template with Swedish colors
- [x] Bottom navigation (4 tabs)
- [x] Home tab with placeholder content
- [x] Scenarios tab with list view
- [x] Scenario detail page with word list
- [x] Vocabulary tab with search and filters

### Phase 3: Learning Engine (Week 3) ✅ COMPLETE
- [x] Mastery calculation service
- [x] Adaptive session word selection
- [x] Exercise components:
  - [x] Read exercise (Swedish → English)
  - [x] Listen exercise (Audio → English)
  - [x] Speak exercise (pronunciation with Web Speech API)
  - [x] Write exercise (jumbled letters)
- [x] Session flow controller
- [x] Session completion summary

### Phase 4: Progress & Stats (Week 4) ✅ COMPLETE
- [x] Streak tracking logic
- [x] Time tracking per session
- [x] Statistics page
- [x] Word status computation
- [x] Progress percentages per scenario
- [x] "Already known" marking feature

### Phase 5: Authentication (Week 5)
- [ ] User model and auth tables
- [ ] Google OAuth integration
- [ ] Apple Sign-In integration
- [ ] Email/password auth
- [ ] Session management
- [ ] User data persistence

### Phase 6: Polish & Content (Week 6)
- [ ] Import remaining vocabulary (2000+ words)
- [ ] UI polish and animations
- [ ] Error handling improvements
- [ ] Performance optimization
- [ ] Testing
- [ ] PWA setup (manifest, service worker)

### Phase 7: Launch Prep (Week 7)
- [ ] Landing page
- [ ] Privacy policy, terms of service
- [ ] Deployment setup
- [ ] Monitoring and analytics
- [ ] Beta testing
- [ ] Launch! 🚀

---

## ✅ Features Included in v1

- [x] Scenario-based vocabulary organization
- [x] 4-skill learning (Read, Listen, Speak, Write)
- [x] Adaptive learning algorithm
- [x] Single status per word (Not started / In progress / Mastered / Already known)
- [x] Streak tracking
- [x] Time spent tracking
- [x] Statistics page
- [x] Search within vocabulary
- [x] "Already known" manual marking
- [x] Swedish TTS pronunciation
- [x] Speech recognition for Speak exercises
- [x] Google/Apple/Email authentication
- [x] Dark theme with Swedish colors
- [x] Mobile-responsive design

## ❌ Features Excluded from v1

- [ ] Gem/currency system
- [ ] Favorites
- [ ] Sort options
- [ ] Custom word lists ("My Lists")
- [ ] User-added words
- [ ] Reverse direction testing (English → Swedish for Read/Listen)
- [ ] Offline mode
- [ ] Daily plan/forced schedule
- [ ] Images for words
- [ ] Achievements/badges

---

## 🤖 Agent Development Instructions

This project is developed using **Claude Code**. To manage context limits:

1. **Always read these files first**:
   - `VOCABESTIE_PLAN.md` (this file) — product context
   - `VOCABESTIE_PROGRESS.md` — current state and next tasks

2. **Update progress file** at the end of each session

3. **Keep commits atomic** — one feature per commit

4. **Follow the phase order** — don't skip ahead

### Starting a Claude Code Session

```bash
cd ~/projects/vocabestie
claude
```

Then paste:
```
Read VOCABESTIE_PLAN.md and VOCABESTIE_PROGRESS.md to understand the project. 
This is a Swedish vocabulary learning app with scenario-based learning and 4-skill mastery (Read, Listen, Speak, Write).
Let's continue from where we left off.
```

---

## 📝 Key Terminology

| Term | Definition |
|------|------------|
| **Scenario** | A realistic situation grouping related words (e.g., "At the Office") |
| **Mastered** | Word status when all 4 skills are above 0.8 threshold |
| **Already known** | Manual status set by user to skip a word |
| **Session** | A learning session where user practices words across skills |
| **Mastery score** | 0.0-1.0 value per skill indicating proficiency |

---

*This plan is the source of truth for Vocabestie development. Update as the product evolves.*
