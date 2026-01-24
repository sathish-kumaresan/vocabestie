from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Word, ReviewCard
from app.schemas import WordResponse, ReviewRequest
from app.services import SpacedRepetitionService

router = APIRouter(prefix="/flashcards", tags=["flashcards"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def flashcards_page(request: Request, db: Session = Depends(get_db)):
    """Render the flashcards page."""
    return templates.TemplateResponse("flashcard.html", {"request": request})


@router.get("/api/due", response_model=List[WordResponse])
def get_due_cards(limit: int = 10, db: Session = Depends(get_db)):
    """Get words that are due for review."""
    today = date.today()
    due_cards = (
        db.query(Word)
        .join(ReviewCard)
        .filter(ReviewCard.next_review <= today)
        .order_by(ReviewCard.next_review)
        .limit(limit)
        .all()
    )
    return due_cards


@router.get("/api/next", response_model=Optional[WordResponse])
def get_next_card(db: Session = Depends(get_db)):
    """Get the next word due for review."""
    today = date.today()
    word = (
        db.query(Word)
        .join(ReviewCard)
        .filter(ReviewCard.next_review <= today)
        .order_by(ReviewCard.next_review)
        .first()
    )
    return word


@router.post("/api/{word_id}/review", response_model=WordResponse)
def review_card(word_id: int, review: ReviewRequest, db: Session = Depends(get_db)):
    """Submit a review for a flashcard."""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    if not word.review_card:
        raise HTTPException(status_code=404, detail="Review card not found")

    # Update the review card using SM-2 algorithm
    SpacedRepetitionService.update_card(word.review_card, review.quality)
    db.commit()
    db.refresh(word)

    return word


@router.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get flashcard statistics."""
    today = date.today()
    total = db.query(Word).count()
    due_today = (
        db.query(Word)
        .join(ReviewCard)
        .filter(ReviewCard.next_review <= today)
        .count()
    )
    reviewed_today = (
        db.query(ReviewCard)
        .filter(ReviewCard.last_reviewed != None)
        .filter(ReviewCard.next_review > today)
        .count()
    )

    return {
        "total_words": total,
        "due_today": due_today,
        "reviewed_today": reviewed_today,
    }
