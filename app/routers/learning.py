"""
Learning router for exercise flow and session management.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.models import Scenario, Word
from app.services.session import (
    select_session_words,
    get_exercise_for_word,
    check_answer,
    GUEST_USER_ID,
)
from app.services.mastery import update_mastery, get_word_mastery
from app.services.stats import record_session_completion, get_scenario_progress

router = APIRouter(prefix="/learn", tags=["learning"])
templates = Jinja2Templates(directory="app/templates")


class AnswerRequest(BaseModel):
    word_id: int
    skill_type: str
    answer: str


class AnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    new_mastery: float
    message: str


@router.get("/scenario/{scenario_id}", response_class=HTMLResponse)
def start_learning_session(
    scenario_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Start a learning session for a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Select words for session
    words = select_session_words(db, scenario_id, GUEST_USER_ID)

    if not words:
        return templates.TemplateResponse("learning/no_words.html", {
            "request": request,
            "scenario": scenario,
        })

    # Get first exercise
    skill_type, exercise_data = get_exercise_for_word(db, words[0], GUEST_USER_ID)

    # Store session data (word IDs) in template
    word_ids = [w.id for w in words]

    return templates.TemplateResponse("learning/session.html", {
        "request": request,
        "scenario": scenario,
        "exercise": exercise_data,
        "skill_type": skill_type,
        "word_ids": word_ids,
        "current_index": 0,
        "total_words": len(words),
    })


@router.get("/exercise/{word_id}", response_class=HTMLResponse)
def get_exercise(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
    word_ids: str = "",  # Comma-separated list of word IDs
    current_index: int = 0,
):
    """Get exercise for a specific word."""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    skill_type, exercise_data = get_exercise_for_word(db, word, GUEST_USER_ID)

    # Parse word_ids
    word_id_list = [int(x) for x in word_ids.split(",") if x] if word_ids else [word_id]
    total_words = len(word_id_list)

    # Determine template based on skill type
    template_name = f"learning/exercise_{skill_type}.html"

    return templates.TemplateResponse(template_name, {
        "request": request,
        "exercise": exercise_data,
        "skill_type": skill_type,
        "word_ids": word_ids,
        "current_index": current_index,
        "total_words": total_words,
    })


@router.post("/answer", response_model=AnswerResponse)
def submit_answer(
    answer_req: AnswerRequest,
    db: Session = Depends(get_db),
):
    """Submit an answer and get feedback."""
    word = db.query(Word).filter(Word.id == answer_req.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    # Determine correct answer based on skill type
    if answer_req.skill_type in ['read', 'listen']:
        correct_answer = word.english
    else:  # speak, write
        correct_answer = word.swedish

    # Check answer
    is_correct, accuracy = check_answer(
        answer_req.skill_type,
        answer_req.answer,
        correct_answer,
    )

    # Update mastery
    new_mastery = update_mastery(
        db,
        GUEST_USER_ID,
        word.id,
        answer_req.skill_type,
        is_correct,
    )

    # Generate message
    if is_correct:
        messages = ["Correct!", "Well done!", "Perfect!", "Great job!"]
        import random
        message = random.choice(messages)
    else:
        message = f"The correct answer is: {correct_answer}"

    return AnswerResponse(
        correct=is_correct,
        correct_answer=correct_answer,
        new_mastery=new_mastery,
        message=message,
    )


@router.get("/complete", response_class=HTMLResponse)
def session_complete(
    request: Request,
    scenario_id: int,
    words_practiced: int = 0,
    correct_count: int = 0,
    time_seconds: int = 0,
    db: Session = Depends(get_db),
):
    """Show session completion summary."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()

    accuracy = (correct_count / words_practiced * 100) if words_practiced > 0 else 0

    # Record session completion in stats
    session_stats = record_session_completion(
        db=db,
        user_id=GUEST_USER_ID,
        words_practiced=words_practiced,
        exercises_completed=words_practiced,  # One exercise per word
        time_seconds=time_seconds,
    )

    # Get updated scenario progress
    scenario_progress = get_scenario_progress(db, scenario_id, GUEST_USER_ID)

    return templates.TemplateResponse("learning/complete.html", {
        "request": request,
        "scenario": scenario,
        "words_practiced": words_practiced,
        "correct_count": correct_count,
        "accuracy": round(accuracy),
        "time_seconds": time_seconds,
        "current_streak": session_stats["current_streak"],
        "scenario_progress": scenario_progress["progress_percent"],
    })
