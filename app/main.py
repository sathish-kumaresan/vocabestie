from typing import Optional
import math
from fastapi import FastAPI, Request, Depends, Query, HTTPException, Cookie
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_db
from app.config import settings
from app.models import Scenario, Word
from app.routers import scenarios_router, words_router, learning_router, auth_router, speech_router
from app.services.stats import get_user_statistics, get_scenario_progress, get_word_statuses_bulk
from app.dependencies import get_user_id, get_auth_context

app = FastAPI(
    title="Vocabestie",
    description="Learn Swedish vocabulary with scenario-based learning and 4-skill mastery",
    version="2.0.0",
)

# Add session middleware for OAuth state
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routers
app.include_router(scenarios_router)
app.include_router(words_router)
app.include_router(learning_router)
app.include_router(auth_router)
app.include_router(speech_router)

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Home page with stats and quick actions."""
    from app.services.session_manager import get_active_session
    
    total_words = db.query(Word).count()
    total_scenarios = db.query(Scenario).count()
    stats = get_user_statistics(db, user_id)
    
    # Determine where "Start/Continue" should go
    active_session = get_active_session(db, user_id)
    if active_session:
        next_scenario_id = active_session.scenario_id
    else:
        # Default to Scenario 1 (Intro) for now
        # Improvement: Could find first incomplete scenario
        next_scenario_id = 1

    return templates.TemplateResponse("home.html", {
        "request": request,
        "active_tab": "home",
        "total_words": total_words,
        "total_scenarios": total_scenarios,
        "stats": stats,
        "next_scenario_id": next_scenario_id,
        **auth,
    })


@app.get("/levels", response_class=HTMLResponse)
def levels_page(
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Levels landing page with CEFR groups (A1-C2)."""
    # Use the new optimized aggregator
    from app.services.stats import get_cefr_progress
    
    cefr_stats = get_cefr_progress(db, user_id)
    
    # CEFR definitions for UI
    cefr_levels = [
        {"id": "A1", "name": "Beginner", "desc": "Basic everyday interactions", "color": "text-green-300"},
        {"id": "A2", "name": "Elementary", "desc": "Simple personal information", "color": "text-green-400"},
        {"id": "B1", "name": "Intermediate", "desc": "Work, school, leisure", "color": "text-yellow-300"},
        {"id": "B2", "name": "Upper Intermediate", "desc": "Regular interaction", "color": "text-yellow-400"},
        {"id": "C1", "name": "Advanced", "desc": "Effective operational proficiency", "color": "text-red-300"},
        {"id": "C2", "name": "Mastery", "desc": "Spontaneous, fluent translation", "color": "text-red-400"},
    ]
    
    # Merge stats into definition and compute locking
    levels_data = []
    previous_level_mastered = True  # First level (A1) is always unlocked
    
    for level in cefr_levels:
        stats = cefr_stats.get(level["id"], {})
        
        # Check mastery of THIS level for the NEXT iteration
        # Mastered if mastered count == total words (and total > 0)
        total = stats.get("total_words", 0)
        mastered = stats.get("mastered", 0)
        is_mastered = (total > 0 and mastered == total)
        
        # Determine locked status
        # Locked if previous level was NOT mastered
        is_locked = not previous_level_mastered
        
        levels_data.append({
            **level,
            "stats": stats,
            "locked": is_locked
        })
        
        # Update flag for next level
        previous_level_mastered = is_mastered

    return templates.TemplateResponse("scenarios.html", {
        "request": request,
        "active_tab": "levels",
        "levels": levels_data,
        **auth,
    })


@app.get("/levels/{level_id}", response_class=HTMLResponse)
def level_detail_page(
    level_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=100),
    words_per_page: Optional[int] = Cookie(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Level detail page showing NEXT words to learn (excluding mastered/known)."""
    from app.services.stats import get_word_status_for_display, get_scenario_progress, get_word_statuses_bulk
    import math
    
    # Resolving limit from query or cookie
    limit = limit or words_per_page or 10
    
    # Flattened structure: 1 scenario per level
    scenario = db.query(Scenario).filter(Scenario.difficulty_level == level_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Level {level_id} not found")

    # 1. Fetch ALL words for this level (ordered)
    all_words = (
        db.query(Word)
        .filter(Word.scenario_id == scenario.id)
        .order_by(Word.display_order)
        .all()
    )

    # 2. Get status for ALL words efficiently
    all_word_ids = [w.id for w in all_words]
    bulk_statuses = get_word_statuses_bulk(db, all_word_ids, user_id)

    # 3. Filter: Keep only 'in_progress' and 'not_started'
    filtered_words = []
    for word in all_words:
        status_info = bulk_statuses.get(word.id, {"status": "not_started"})
        if status_info["status"] not in ("mastered", "already_known"):
            filtered_words.append({
                "word": word,
                "status": status_info
            })

    # 4. Pagination on filtered list
    total_words = len(filtered_words)
    total_pages = math.ceil(total_words / limit) if total_words > 0 else 1
    
    # Ensure page is within bounds
    if page > total_pages: page = total_pages
    if page < 1: page = 1
    
    offset = (page - 1) * limit
    paginated_words = filtered_words[offset : offset + limit]

    # Get progress (for the whole level)
    progress = get_scenario_progress(db, scenario.id, user_id)

    return templates.TemplateResponse("scenario_detail.html", {
        "request": request,
        "active_tab": "levels",
        "scenario": scenario,
        "words": paginated_words,
        "progress": progress,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_words": total_words,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1,
            "prev_page": page - 1
        },
        **auth,
    })


@app.get("/scenarios/{scenario_id}", response_class=HTMLResponse)
def scenario_detail_page(
    scenario_id: int,
    request: Request,
    page: int = Query(1, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=100),
    words_per_page: Optional[int] = Cookie(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Scenario detail page with word list and progress."""
    from app.services.stats import get_word_status_for_display, get_scenario_progress, get_word_statuses_bulk
    import math

    # Resolving limit from query or cookie
    limit = limit or words_per_page or 10

    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Pagination Logic
    offset = (page - 1) * limit
    total_words = db.query(Word).filter(Word.scenario_id == scenario_id).count()
    total_pages = math.ceil(total_words / limit) if total_words > 0 else 1

    # Ensure page is within bounds
    if page > total_pages: page = total_pages
    if page < 1: page = 1

    # Fetch words for this level (paginated)
    words = (
        db.query(Word)
        .filter(Word.scenario_id == scenario_id)
        .order_by(Word.display_order)
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Get progress for scenario and each word
    progress = get_scenario_progress(db, scenario_id, user_id)
    
    # Get status for the paginated words efficiently
    word_ids_on_page = [word.id for word in words]
    bulk_statuses = get_word_statuses_bulk(db, word_ids_on_page, user_id)

    words_with_status = []
    for word in words:
        status = get_word_status_for_display(db, word.id, user_id)
        words_with_status.append({
            "word": word,
            "status": status,
        })

    return templates.TemplateResponse("scenario_detail.html", {
        "request": request,
        "active_tab": "levels",
        "scenario": scenario,
        "words": words_with_status,
        "progress": progress,
        **auth,
    })


@app.get("/vocabulary/{word_id}", response_class=HTMLResponse)
def word_details_page(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Detailed view for a single vocabulary word."""
    from app.services.stats import get_word_status_for_display
    
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
        
    status = get_word_status_for_display(db, word.id, user_id)
    
    return templates.TemplateResponse("word_details.html", {
        "request": request,
        "active_tab": "vocabulary",
        "word": word,
        "status": status,
        **auth,
    })


@app.get("/vocabulary", response_class=HTMLResponse)
def vocabulary_page(
    request: Request,
    db: Session = Depends(get_db),
    filter: str = "all",
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Vocabulary list page with server-side pagination and search."""
    
    # Base query
    query = db.query(Word)

    # 1. Apply Search
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Word.swedish.ilike(search_term)) | (Word.english.ilike(search_term))
        )

    # 2. Apply Status Filter (requires join if not 'all')
    # Note: Filtering by status in SQL is complex because status is computed.
    # ideally we denormalize status or accept that 'all' is fast and status filters 
    # might require more complex queries. For now, we'll keep the status filter logic
    # simple: if filtered by status, we might need to fetch more and filter in python
    # OR we join with the mastery table. 
    # To keep it performant for now:
    # - "all": simple pagination
    # - "status": fetch potential candidates (or all) and filter? 
    # With 8000 words, fetching all IDs to filter is lighter than fetching all objects.
    
    # OPTIMIZATION: For this iteration, we will implement accurate pagination for "all" 
    # and "search". For status filters, we accept a potential performance hit or 
    # we implement a smart join.
    # Given the requirements, let's try to do it right with joins if possible, 
    # BUT "status" calculation involves multiple skills and thresholds.
    # A simplified approach for V2:
    # - Filter = 'already_known': Easy, join UserWordStatus
    # - Filter = 'not_started': Harder (no mastery record OR all 0)
    # 
    # allow_filtering_by_status_in_db = False 
    
    # If we filter by status, we really need to do it in memory for 8k words? 
    # 8k words in memory is actually fine for python if we just fetch IDs and scores. 
    # Let's try a hybrid approach: 
    # If filter is specific, we might just get all IDs, compute status, filter IDs, then paginate.
    
    total_words_count = db.query(Word).count()
    matching_words_query = query # Keep reference for counting search results
    
    # Counts for tabs (always needed) - this is the heavy part if done naively.
    # We can cache these or accept the cost. For 8000 words, fetching all skill masteries 
    # for a user is ~8000 rows. Fast enough.
    
    # Let's fetch ALL word statuses for the user to do counts and filtering accurately.
    # fetch all word IDs
    all_words = db.query(Word.id).all()
    all_word_ids = [w[0] for w in all_words]
    
    # Bulk fetch statuses for ALL words (optimized function needed?)
    # Calling get_word_statuses_bulk with 8000 IDs might be too much for one query parameter
    # but okay for body or chunking. 
    # Actually, fetching all mastery rows for a user is better.
    
    # optimization: Status counts based on separate efficient queries
    # For now, let's keep the user experience good:
    
    if filter != "all":
        # If filtering, we need to fetch all to filter. 
        # But we can optimize: "already_known" is a simple query.
        pass
        
    # PAGE SIZE
    PAGE_SIZE = 50
    
    # Execute query with pagination
    # If filtering by status, we have to do it in memory or complex SQL.
    # Let's stick to Server-Side Pagination for "All" and "Search" as primary fix.
    # For status filters, if the user selects "Mastered", we might just show them all
    # or rely on frontend if the set is small. But "Not Started" is huge.
    
    # DECISION: To ensure consistency, we will fetch the data for the current page.
    # However, filtering by computed status AND paginating is hard. 
    # We will implement logic to filtering by status if requested.
    
    filtered_word_ids = []
    
    # Helper to get all IDs matching search
    # We fetch (id, swedish, difficulty_level) to sort in Python
    candidates = matching_words_query.with_entities(Word.id, Word.swedish, Word.difficulty_level).all()
    
    def swedish_sort_key(pair):
        # pair is (id, swedish_word, difficulty_level)
        w = pair[1].lower().strip()
        # Map å->{, ä->|, ö->} to fix Ä coming before Å in unicode
        tr = w.translate(str.maketrans({
            'å': '{',
            'ä': '|',
            'ö': '}'
        }))
        return tr

    # Sort candidates in Python: Length first, then Level, then Swedish Alpha
    # Tuple sort: (length, difficulty_level, swedish_normalized_string)
    # Note: difficulty_level (A1, A2...) sorts correctly alphabetically
    candidates.sort(key=lambda x: (len(x[1]), x[2] or "", swedish_sort_key(x)))
    candidate_ids = [c[0] for c in candidates]
    
    # logic below handles pagination for all filters
    try:
        # logic below handles pagination for all filters
        # --- UNIFIED STATUS CALCULATION & FILTERING ---
        from app.models.mastery import UserWordStatus, WordSkillMastery
        from app.services.stats import PASS_THRESHOLD
        
        # 1. Get Known Overrides
        known_ids_set = {x[0] for x in db.query(UserWordStatus.word_id).filter(UserWordStatus.user_id == user_id, UserWordStatus.status == 'already_known').all()}
        
        # 2. Get Masteries
        raw_masteries = db.query(WordSkillMastery.word_id, WordSkillMastery.skill_type, WordSkillMastery.mastery_score).filter(WordSkillMastery.user_id == user_id).all()
        
        w_map = {}
        for r in raw_masteries:
            if r.word_id not in w_map: w_map[r.word_id] = {}
            w_map[r.word_id][r.skill_type] = r.mastery_score
            
        counts = {"all": len(candidate_ids), "not_started": 0, "in_progress": 0, "mastered": 0}
        
        final_ids = []
        
        for wid in candidate_ids:
            status = "not_started"
            
            # Check Known Override FIRST (Treat as Mastered)
            if wid in known_ids_set:
                status = "mastered"
            
            # Check Skills
            elif wid in w_map:
                skills = w_map[wid]
                # Check for Mastered: Average > 90%
                skill_scores = [skills.get(s, 0.0) for s in ['read', 'listen', 'speak', 'write']]
                avg_score = sum(skill_scores) / 4.0
                
                if avg_score > 0.9:
                    status = "mastered"
                elif all(s == 0 for s in skill_scores):
                     # If all scores are 0, it is not started (even if record exists)
                     status = "not_started"
                else:
                     status = "in_progress"
            
            counts[status] += 1
            
            if filter == "all" or filter == status:
                final_ids.append(wid)
                
        total_items = len(final_ids)
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_ids = final_ids[start_idx:end_idx]

        # --- FETCH WORDS AND STATUSES FOR PAGE ---
        words = db.query(Word).filter(Word.id.in_(page_ids)).all()
        word_map_obj = {w.id: w for w in words}
        
        statuses = get_word_statuses_bulk(db, page_ids, user_id)
        
        words_with_status = []
        for wid in page_ids:
            if wid in word_map_obj:
                entry = statuses.get(wid, {})
                entry['word'] = word_map_obj[wid]
                words_with_status.append(entry)

        total_words_count = total_items
        total_pages = math.ceil(total_items / PAGE_SIZE)
        if total_pages == 0: total_pages = 1

        return templates.TemplateResponse("vocabulary.html", {
            "request": request,
            "active_tab": "vocabulary",
            "words": words_with_status,
            "total_words": total_words_count,
            "current_filter": filter,
            "counts": counts,
            "current_page": page,
            "total_pages": total_pages,
            "search_query": search or "",
            **auth,
        })
    except Exception as e:
        import logging
        logging.exception("Error in vocabulary page")
        return HTMLResponse(content="An error occurred. Please try again.", status_code=500)


@app.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Settings page with real statistics."""
    stats = get_user_statistics(db, user_id)

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active_tab": "settings",
        "stats": stats,
        **auth,
    })


@app.get("/api/audio/tts")
def get_tts_audio(text: str):
    """Generates (if needed) and returns path to audio file."""
    from app.services.audio import get_audio_path
    
    if not text:
        raise HTTPException(status_code=400, detail="Text required")
        
    audio_url = get_audio_path(text)
    if not audio_url:
        raise HTTPException(status_code=500, detail="Audio generation failed")
        
    return {"audio_url": audio_url}





@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}
