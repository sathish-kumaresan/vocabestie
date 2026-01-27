from typing import Optional
import math
from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_db
from app.config import settings
from app.models import Scenario, Word
from app.routers import scenarios_router, words_router, learning_router, auth_router
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
    total_words = db.query(Word).count()
    total_scenarios = db.query(Scenario).count()
    stats = get_user_statistics(db, user_id)

    return templates.TemplateResponse("home.html", {
        "request": request,
        "active_tab": "home",
        "total_words": total_words,
        "total_scenarios": total_scenarios,
        "stats": stats,
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
        {"id": "A1", "name": "Beginner", "desc": "Basic everyday interactions", "color": "text-green-400"},
        {"id": "A2", "name": "Elementary", "desc": "Simple personal information", "color": "text-green-300"},
        {"id": "B1", "name": "Intermediate", "desc": "Work, school, leisure", "color": "text-yellow-400"},
        {"id": "B2", "name": "Upper Intermediate", "desc": "Regular interaction", "color": "text-yellow-300"},
        {"id": "C1", "name": "Advanced", "desc": "Effective operational proficiency", "color": "text-red-400"},
        {"id": "C2", "name": "Mastery", "desc": "Spontaneous, fluent translation", "color": "text-red-300"},
    ]
    
    # Merge stats into definition
    levels_data = []
    for level in cefr_levels:
        stats = cefr_stats.get(level["id"], {})
        levels_data.append({
            **level,
            "stats": stats
        })

    return templates.TemplateResponse("scenarios.html", {
        "request": request,
        "active_tab": "levels",
        "levels": levels_data,
        **auth,
    })


@app.get("/levels/{difficulty}", response_class=HTMLResponse)
def level_detail_page(
    difficulty: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Drill-down page for a specific CEFR level (listing scenarios)."""
    from app.services.stats import get_scenarios_progress_bulk
    
    # Validate difficulty
    if difficulty not in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "message": "Level not found",
            **auth,
        }, status_code=404)
        
    # Fetch scenarios for this level
    scenarios = db.query(Scenario).filter(
        Scenario.difficulty_level == difficulty
    ).order_by(Scenario.display_order).all()
    
    # Bulk fetch progress
    if scenarios:
        scenario_ids = [s.id for s in scenarios]
        progress_map = get_scenarios_progress_bulk(db, scenario_ids, user_id)
    else:
        progress_map = {}
        
    scenarios_data = []
    for s in scenarios:
        scenarios_data.append({
            "scenario": s,
            "progress": progress_map.get(s.id, {"progress_percent": 0})
        })
        
    return templates.TemplateResponse("level_detail.html", {
        "request": request,
        "active_tab": "levels",
        "difficulty": difficulty,
        "scenarios": scenarios_data,
        **auth,
    })


@app.get("/scenarios/{scenario_id}", response_class=HTMLResponse)
def scenario_detail_page(
    scenario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Scenario detail page with word list and progress."""
    from app.services.stats import get_word_status_for_display

    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "message": "Scenario not found",
            **auth,
        }, status_code=404)

    words = (
        db.query(Word)
        .filter(Word.scenario_id == scenario_id)
        .order_by(Word.display_order)
        .all()
    )

    # Get progress for scenario and each word
    progress = get_scenario_progress(db, scenario_id, user_id)
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
    candidates = matching_words_query.with_entities(Word.id).order_by(Word.swedish).all()
    candidate_ids = [c[0] for c in candidates]
    
    if filter == "all":
        # Simple case: just paginate the ids
        total_items = len(candidate_ids)
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_ids = candidate_ids[start_idx:end_idx]
    else:
        # Complex case: We need to check status for candidates until we fill the page? 
        # OR we just get statuses for ALL candidates (8000) and filters.
        # Fetching 8000 statuses in memory is faster than N+1 queries.
        
        # Get all masteries for user
        # We'll use a specific service method for this if getting too complex, 
        # but let's try to utilize `get_word_statuses_bulk` but maybe chunked?
        # Actually, let's fetch all relevant data and filter in python.
        
        # 1. Get Known Words
        from app.models import UserWordStatus
        known_overrides = db.query(UserWordStatus.word_id).filter(
            UserWordStatus.user_id == user_id, 
            UserWordStatus.status == 'already_known'
        ).all()
        known_ids = {k[0] for k in known_overrides}
        
        # 2. Get Masteries
        from app.models import WordSkillMastery
        user_masteries = db.query(WordSkillMastery).filter(
            WordSkillMastery.user_id == user_id
        ).all()
        
        # Build status map
        # word_id -> {skill: score}
        word_mastery_map = {}
        for m in user_masteries:
            if m.word_id not in word_mastery_map:
                word_mastery_map[m.word_id] = {}
            word_mastery_map[m.word_id][m.skill_type] = m.mastery_score
            
        final_ids = []
        
        from app.services.mastery import PASS_THRESHOLD
        
        counts = {"all": len(candidate_ids), "not_started": 0, "in_progress": 0, "mastered": 0, "already_known": 0}
        
        for wid in candidate_ids:
            status = "not_started"
            if wid in known_ids:
                status = "already_known"
            elif wid in word_mastery_map:
                skills = word_mastery_map[wid]
                # Default 0 if missing skills
                skill_scores = [skills.get(s, 0.0) for s in ['read', 'listen', 'speak', 'write']]
                if all(s >= PASS_THRESHOLD for s in skill_scores):
                    status = "mastered"
                elif all(s == 0 for s in skill_scores):
                    status = "not_started" # Should be covered but just in case
                else:
                    status = "in_progress"
            else:
                 status = "not_started"
                 
            counts[status] += 1
            
            if status == filter:
                final_ids.append(wid)
                
        total_items = len(final_ids)
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_ids = final_ids[start_idx:end_idx]
        
    # Now we have the IDs for the current page. Fetch the actual Word objects and formatted statuses.
    words = db.query(Word).filter(Word.id.in_(page_ids)).order_by(Word.swedish).all()
    # Sort words to match the ID order (which was sorted by Swedish)
    words_map = {w.id: w for w in words}
    ordered_words = [words_map[wid] for wid in page_ids if wid in words_map]
    
    # Bulk fetch full status details for display
    statuses = get_word_statuses_bulk(db, page_ids, user_id)
    
    words_with_status = []
    for word in ordered_words:
        words_with_status.append({
            "word": word,
            "status": statuses.get(word.id)
        })

    # Recalculate counts if we didn't do the full loop (e.g. filter="all")
    if filter == "all":
         # We still need counts for the tabs... 
         # This is the tradeoff. For now, let's keep the counts accurate only if filter is active
         # OR we do a separate quick count query.
         # For speed, let's approximate or load on demand? 
         # The user wants "Levels" page fixed too.
         # Let's do the "Get counts" logic cleanly:
         # It's actually fast to just query the counts from DB directly.
         pass
         # TODO: optimize counts. utilizing the loop above is ok for 8k items in memory (milliseconds).
         # So maybe we ALWAYS run the loop to get counts, but only hydrate objects for the page.
         
         # Re-running the loop logic for "all" case to get accurate counts:
         if filter == "all":
            # Repatriate the logic to avoid code duplication? 
            # Ideally we refactor this service-side.
            # FASTEST WAY:
            # 1. Get all candidate IDs (search applied)
            # 2. Get all user masteries and known overrides
            # 3. Iterate in python to count and filter
            
            # COPYING LOGIC for "all" filter just to get counts
            from app.models import UserWordStatus, WordSkillMastery
            from app.services.mastery import PASS_THRESHOLD
            
            known_ids_set = {x[0] for x in db.query(UserWordStatus.word_id).filter(UserWordStatus.user_id == user_id, UserWordStatus.status == 'already_known').all()}
            
            # Fetch minimal data for mastery: word_id, skill_type, score
            # Optimization: 1 query
            raw_masteries = db.query(WordSkillMastery.word_id, WordSkillMastery.skill_type, WordSkillMastery.mastery_score).filter(WordSkillMastery.user_id == user_id).all()
            
            w_map = {}
            for r in raw_masteries:
                 if r.word_id not in w_map: w_map[r.word_id] = []
                 w_map[r.word_id].append(r.mastery_score)
            
            counts = {"all": len(candidate_ids), "not_started": 0, "in_progress": 0, "mastered": 0, "already_known": 0}
            
            for wid in candidate_ids:
                if wid in known_ids_set:
                    counts["already_known"] += 1
                elif wid in w_map:
                    scores = w_map[wid]
                    # We need to know if we have 4 skills... 
                    # If less than 4 skills, others are 0.
                    # Simplified status check:
                    if len(scores) < 4: 
                        # HAS SOME SKILLS
                         # If any existing is < threshold -> in_progress (since missing are 0)
                         # If all existing > threshold -> still in_progress (missing are 0)
                         # UNLESS missing skills don't exist? No, 4 skills always exist conceptually.
                         counts['in_progress'] += 1
                    else:
                        if all(s >= PASS_THRESHOLD for s in scores):
                            counts['mastered'] += 1
                        else:
                            counts['in_progress'] += 1
                else:
                    counts['not_started'] += 1

    total_pages = math.ceil(total_items / PAGE_SIZE)

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


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}
