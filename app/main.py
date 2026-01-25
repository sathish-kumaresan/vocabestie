from datetime import date
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Word, ReviewCard, QuizAttempt
from app.routers import words_router, flashcards_router, quiz_router

app = FastAPI(
    title="Vocabestie",
    description="A vocabulary learning app with flashcards, quizzes, and spaced repetition",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(words_router)
app.include_router(flashcards_router)
app.include_router(quiz_router)

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, db: Session = Depends(get_db)):
    """Statistics page."""
    today = date.today()

    # Word stats
    total_words = db.query(Word).count()
    due_today = (
        db.query(Word)
        .join(ReviewCard)
        .filter(ReviewCard.next_review <= today)
        .count()
    )

    # Quiz stats
    quiz_attempts = db.query(QuizAttempt).count()
    quiz_correct = db.query(QuizAttempt).filter(QuizAttempt.correct == True).count()
    quiz_accuracy = round((quiz_correct / quiz_attempts * 100) if quiz_attempts > 0 else 0, 1)

    # Quiz by type
    quiz_by_type = {}
    type_counts = (
        db.query(QuizAttempt.quiz_type, func.count(QuizAttempt.id))
        .group_by(QuizAttempt.quiz_type)
        .all()
    )
    for quiz_type, count in type_counts:
        quiz_by_type[quiz_type.value] = count

    # Spaced repetition stats
    total_reviews = db.query(ReviewCard).filter(ReviewCard.repetitions > 0).count()
    sr_new = db.query(ReviewCard).filter(ReviewCard.repetitions == 0).count()
    sr_learning = db.query(ReviewCard).filter(ReviewCard.repetitions.between(1, 3)).count()
    sr_mature = db.query(ReviewCard).filter(ReviewCard.repetitions >= 4).count()

    stats = {
        "total_words": total_words,
        "due_today": due_today,
        "quiz_attempts": quiz_attempts,
        "quiz_correct": quiz_correct,
        "quiz_accuracy": quiz_accuracy,
        "quiz_by_type": quiz_by_type,
        "total_reviews": total_reviews,
        "sr_new": sr_new,
        "sr_learning": sr_learning,
        "sr_mature": sr_mature,
    }

    return templates.TemplateResponse("stats.html", {"request": request, "stats": stats})


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}
