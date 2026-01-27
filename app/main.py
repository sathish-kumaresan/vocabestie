from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_db
from app.config import settings
from app.models import Scenario, Word
from app.routers import scenarios_router, words_router, learning_router, auth_router
from app.services.stats import get_user_statistics, get_scenario_progress
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


@app.get("/scenarios", response_class=HTMLResponse)
def scenarios_page(
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Scenarios list page with progress."""
    scenarios = db.query(Scenario).order_by(Scenario.display_order).all()

    # Calculate progress for each scenario
    scenarios_with_progress = []
    for scenario in scenarios:
        progress = get_scenario_progress(db, scenario.id, user_id)
        scenarios_with_progress.append({
            "scenario": scenario,
            "progress": progress,
        })

    return templates.TemplateResponse("scenarios.html", {
        "request": request,
        "active_tab": "scenarios",
        "scenarios": scenarios_with_progress,
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
        "active_tab": "scenarios",
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
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Vocabulary list page with status filters."""
    from app.services.stats import get_word_status_for_display

    words = db.query(Word).order_by(Word.swedish).all()
    total_words = len(words)

    # Get status for each word and apply filter
    words_with_status = []
    counts = {"all": 0, "not_started": 0, "in_progress": 0, "mastered": 0, "already_known": 0}

    for word in words:
        status = get_word_status_for_display(db, word.id, user_id)
        counts["all"] += 1
        counts[status["status"]] += 1

        # Apply filter
        if filter == "all" or filter == status["status"]:
            words_with_status.append({
                "word": word,
                "status": status,
            })

    return templates.TemplateResponse("vocabulary.html", {
        "request": request,
        "active_tab": "vocabulary",
        "words": words_with_status,
        "total_words": total_words,
        "current_filter": filter,
        "counts": counts,
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
