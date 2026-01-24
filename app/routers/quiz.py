import random
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func

from app.database import get_db
from app.models import Word, QuizAttempt, ReviewCard
from app.models.word import QuizType
from app.schemas import QuizQuestion, QuizAnswer, QuizResult
from app.services import SpacedRepetitionService

router = APIRouter(prefix="/quiz", tags=["quiz"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def quiz_page(request: Request, db: Session = Depends(get_db)):
    """Render the quiz page."""
    total_words = db.query(Word).count()
    return templates.TemplateResponse(
        "quiz.html", {"request": request, "total_words": total_words}
    )


@router.get("/api/question", response_model=QuizQuestion)
def get_quiz_question(db: Session = Depends(get_db)):
    """Generate a multiple choice quiz question."""
    # Get a random word for the question
    word = db.query(Word).order_by(func.random()).first()
    if not word:
        raise HTTPException(status_code=404, detail="No words available for quiz")

    # Get 3 random wrong answers
    wrong_words = (
        db.query(Word)
        .filter(Word.id != word.id)
        .order_by(func.random())
        .limit(3)
        .all()
    )

    if len(wrong_words) < 3:
        raise HTTPException(
            status_code=400,
            detail="Not enough words for quiz. Add at least 4 words.",
        )

    # Build options and shuffle
    options = [word.definition] + [w.definition for w in wrong_words]
    random.shuffle(options)

    return QuizQuestion(
        word_id=word.id,
        term=word.term,
        options=options,
        quiz_type="multiple_choice",
    )


@router.post("/api/answer", response_model=QuizResult)
def submit_answer(answer: QuizAnswer, db: Session = Depends(get_db)):
    """Submit an answer and get the result."""
    word = db.query(Word).filter(Word.id == answer.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    correct = answer.selected_answer == word.definition

    # Record the attempt
    attempt = QuizAttempt(
        word_id=word.id,
        correct=correct,
        quiz_type=QuizType.multiple_choice,
    )
    db.add(attempt)

    # Update spaced repetition if review card exists
    if word.review_card:
        quality = SpacedRepetitionService.get_quality_from_quiz(correct)
        SpacedRepetitionService.update_card(word.review_card, quality)

    db.commit()

    return QuizResult(
        word_id=word.id,
        term=word.term,
        correct=correct,
        correct_answer=word.definition,
        selected_answer=answer.selected_answer,
    )


@router.get("/api/stats")
def get_quiz_stats(db: Session = Depends(get_db)):
    """Get quiz statistics."""
    total_attempts = db.query(QuizAttempt).count()
    correct_attempts = db.query(QuizAttempt).filter(QuizAttempt.correct == True).count()

    accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

    return {
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "accuracy": round(accuracy, 1),
    }
