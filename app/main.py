from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Scenario, Word
from app.routers import scenarios_router, words_router, learning_router

app = FastAPI(
    title="Vocabestie",
    description="Learn Swedish vocabulary with scenario-based learning and 4-skill mastery",
    version="2.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routers
app.include_router(scenarios_router)
app.include_router(words_router)
app.include_router(learning_router)

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """Home page with stats and quick actions."""
    total_words = db.query(Word).count()
    total_scenarios = db.query(Scenario).count()

    return templates.TemplateResponse("home.html", {
        "request": request,
        "active_tab": "home",
        "total_words": total_words,
        "total_scenarios": total_scenarios,
    })


@app.get("/scenarios", response_class=HTMLResponse)
def scenarios_page(request: Request, db: Session = Depends(get_db)):
    """Scenarios list page."""
    scenarios = db.query(Scenario).order_by(Scenario.display_order).all()

    return templates.TemplateResponse("scenarios.html", {
        "request": request,
        "active_tab": "scenarios",
        "scenarios": scenarios,
    })


@app.get("/scenarios/{scenario_id}", response_class=HTMLResponse)
def scenario_detail_page(scenario_id: int, request: Request, db: Session = Depends(get_db)):
    """Scenario detail page with word list."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "message": "Scenario not found",
        }, status_code=404)

    words = (
        db.query(Word)
        .filter(Word.scenario_id == scenario_id)
        .order_by(Word.display_order)
        .all()
    )

    return templates.TemplateResponse("scenario_detail.html", {
        "request": request,
        "active_tab": "scenarios",
        "scenario": scenario,
        "words": words,
    })


@app.get("/vocabulary", response_class=HTMLResponse)
def vocabulary_page(request: Request, db: Session = Depends(get_db)):
    """Vocabulary list page."""
    words = db.query(Word).order_by(Word.swedish).limit(100).all()
    total_words = db.query(Word).count()

    return templates.TemplateResponse("vocabulary.html", {
        "request": request,
        "active_tab": "vocabulary",
        "words": words,
        "total_words": total_words,
    })


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    """Settings page."""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active_tab": "settings",
    })


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}
