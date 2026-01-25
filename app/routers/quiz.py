import random
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from pydantic import BaseModel

from app.database import get_db
from app.models import Word, QuizAttempt, ReviewCard
from app.models.word import QuizType
from app.schemas import QuizQuestion, QuizAnswer, QuizResult
from app.services import SpacedRepetitionService

router = APIRouter(prefix="/quiz", tags=["quiz"])
templates = Jinja2Templates(directory="app/templates")


# Additional schemas for new quiz types
class ListeningQuestion(BaseModel):
    word_id: int
    options: List[str]


class SpellingQuestion(BaseModel):
    word_id: int
    definition: str
    hint: Optional[str] = None


class SpellingAnswer(BaseModel):
    word_id: int
    typed_answer: str


class SpellingResult(BaseModel):
    word_id: int
    correct: bool
    correct_answer: str
    typed_answer: str
    closeness: str  # 'exact', 'close', 'wrong'


class FillBlankQuestion(BaseModel):
    word_id: int
    sentence_with_blank: str
    options: List[str]


# Helper function to calculate string similarity (Levenshtein distance)
def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# ==================== Quiz Hub ====================

@router.get("", response_class=HTMLResponse)
def quiz_hub(request: Request, db: Session = Depends(get_db)):
    """Render the quiz hub page."""
    total_words = db.query(Word).count()
    words_with_examples = db.query(Word).filter(Word.example != None, Word.example != '').count()

    # Get stats
    total_attempts = db.query(QuizAttempt).count()
    correct_attempts = db.query(QuizAttempt).filter(QuizAttempt.correct == True).count()
    accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

    stats = {
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "accuracy": round(accuracy, 1),
    }

    return templates.TemplateResponse(
        "quiz_hub.html",
        {
            "request": request,
            "total_words": total_words,
            "words_with_examples": words_with_examples,
            "stats": stats,
        }
    )


# ==================== Multiple Choice Quiz ====================

@router.get("/multiple-choice", response_class=HTMLResponse)
def multiple_choice_page(request: Request, db: Session = Depends(get_db)):
    """Render the multiple choice quiz page."""
    total_words = db.query(Word).count()
    return templates.TemplateResponse(
        "quiz.html", {"request": request, "total_words": total_words}
    )


@router.get("/api/question", response_model=QuizQuestion)
def get_quiz_question(db: Session = Depends(get_db)):
    """Generate a multiple choice quiz question."""
    word = db.query(Word).order_by(func.random()).first()
    if not word:
        raise HTTPException(status_code=404, detail="No words available for quiz")

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

    # Determine quiz type from answer
    quiz_type_map = {
        "multiple_choice": QuizType.multiple_choice,
        "listening": QuizType.listening,
        "fill_blank": QuizType.fill_blank,
    }
    quiz_type = quiz_type_map.get(answer.quiz_type, QuizType.multiple_choice)

    attempt = QuizAttempt(
        word_id=word.id,
        correct=correct,
        quiz_type=quiz_type,
    )
    db.add(attempt)

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


# ==================== Listening Quiz ====================

@router.get("/listening", response_class=HTMLResponse)
def listening_quiz_page(request: Request, db: Session = Depends(get_db)):
    """Render the listening quiz page."""
    total_words = db.query(Word).count()
    return templates.TemplateResponse(
        "quiz_listening.html", {"request": request, "total_words": total_words}
    )


@router.get("/api/listening/question")
def get_listening_question(db: Session = Depends(get_db)):
    """Generate a listening quiz question (returns word for TTS, no text shown)."""
    word = db.query(Word).order_by(func.random()).first()
    if not word:
        raise HTTPException(status_code=404, detail="No words available")

    wrong_words = (
        db.query(Word)
        .filter(Word.id != word.id)
        .order_by(func.random())
        .limit(3)
        .all()
    )

    if len(wrong_words) < 3:
        raise HTTPException(status_code=400, detail="Not enough words for quiz")

    options = [word.definition] + [w.definition for w in wrong_words]
    random.shuffle(options)

    return {
        "word_id": word.id,
        "term": word.term,  # For TTS only, not displayed
        "options": options,
    }


# ==================== Spelling Quiz ====================

@router.get("/spelling", response_class=HTMLResponse)
def spelling_quiz_page(request: Request, db: Session = Depends(get_db)):
    """Render the spelling quiz page."""
    total_words = db.query(Word).count()
    return templates.TemplateResponse(
        "quiz_spelling.html", {"request": request, "total_words": total_words}
    )


@router.get("/api/spelling/question")
def get_spelling_question(db: Session = Depends(get_db)):
    """Generate a spelling quiz question."""
    word = db.query(Word).order_by(func.random()).first()
    if not word:
        raise HTTPException(status_code=404, detail="No words available")

    # Create hint (first letter + underscores)
    hint = word.term[0] + "_" * (len(word.term) - 1) if word.term else ""

    return {
        "word_id": word.id,
        "definition": word.definition,
        "hint": hint,
        "letter_count": len(word.term),
    }


@router.post("/api/spelling/answer")
def submit_spelling_answer(answer: SpellingAnswer, db: Session = Depends(get_db)):
    """Submit a spelling answer and get the result."""
    word = db.query(Word).filter(Word.id == answer.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    typed = answer.typed_answer.strip().lower()
    correct_term = word.term.lower()

    # Check exactness
    if typed == correct_term:
        correct = True
        closeness = "exact"
    else:
        # Calculate Levenshtein distance for fuzzy matching
        distance = levenshtein_distance(typed, correct_term)
        if distance <= 2 and len(correct_term) > 3:
            correct = False
            closeness = "close"
        else:
            correct = False
            closeness = "wrong"

    attempt = QuizAttempt(
        word_id=word.id,
        correct=correct,
        quiz_type=QuizType.spelling,
    )
    db.add(attempt)

    if word.review_card:
        quality = SpacedRepetitionService.get_quality_from_quiz(correct)
        SpacedRepetitionService.update_card(word.review_card, quality)

    db.commit()

    return {
        "word_id": word.id,
        "correct": correct,
        "correct_answer": word.term,
        "typed_answer": answer.typed_answer,
        "closeness": closeness,
    }


# ==================== Fill in the Blank Quiz ====================

@router.get("/fill-blank", response_class=HTMLResponse)
def fill_blank_quiz_page(request: Request, db: Session = Depends(get_db)):
    """Render the fill in the blank quiz page."""
    total_words = db.query(Word).count()
    words_with_examples = db.query(Word).filter(Word.example != None, Word.example != '').count()
    return templates.TemplateResponse(
        "quiz_fillblank.html",
        {"request": request, "total_words": total_words, "words_with_examples": words_with_examples}
    )


@router.get("/api/fill-blank/question")
def get_fill_blank_question(db: Session = Depends(get_db)):
    """Generate a fill in the blank question."""
    # Get a word that has an example sentence
    word = (
        db.query(Word)
        .filter(Word.example != None, Word.example != '')
        .order_by(func.random())
        .first()
    )

    if not word:
        raise HTTPException(
            status_code=404,
            detail="No words with example sentences available"
        )

    # Get 3 wrong word options
    wrong_words = (
        db.query(Word)
        .filter(Word.id != word.id)
        .order_by(func.random())
        .limit(3)
        .all()
    )

    if len(wrong_words) < 3:
        raise HTTPException(status_code=400, detail="Not enough words for quiz")

    # Replace the word in the example with blanks
    example = word.example
    term_lower = word.term.lower()

    # Try to find and replace the word (case-insensitive)
    import re
    pattern = re.compile(re.escape(word.term), re.IGNORECASE)
    sentence_with_blank = pattern.sub("_____", example)

    # If word wasn't found in example, just append blank
    if sentence_with_blank == example:
        sentence_with_blank = f"_____ : {example}"

    options = [word.term] + [w.term for w in wrong_words]
    random.shuffle(options)

    return {
        "word_id": word.id,
        "sentence_with_blank": sentence_with_blank,
        "options": options,
        "definition": word.definition,
    }


@router.post("/api/fill-blank/answer")
def submit_fill_blank_answer(answer: QuizAnswer, db: Session = Depends(get_db)):
    """Submit a fill in the blank answer."""
    word = db.query(Word).filter(Word.id == answer.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    correct = answer.selected_answer.lower() == word.term.lower()

    attempt = QuizAttempt(
        word_id=word.id,
        correct=correct,
        quiz_type=QuizType.fill_blank,
    )
    db.add(attempt)

    if word.review_card:
        quality = SpacedRepetitionService.get_quality_from_quiz(correct)
        SpacedRepetitionService.update_card(word.review_card, quality)

    db.commit()

    return {
        "word_id": word.id,
        "term": word.term,
        "correct": correct,
        "correct_answer": word.term,
        "selected_answer": answer.selected_answer,
    }


# ==================== Stats ====================

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
