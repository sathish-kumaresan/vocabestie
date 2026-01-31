"""
Learning router for exercise flow and session management.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Request, Query
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
)
from app.services.mastery import update_mastery, get_word_mastery
from app.services.stats import record_session_completion, get_scenario_progress
from app.dependencies import get_user_id, get_auth_context

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
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Start a learning session for a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Select words for session
    words = select_session_words(db, scenario_id, user_id)

    if not words:
        return templates.TemplateResponse("learning/no_words.html", {
            "request": request,
            "scenario": scenario,
            **auth,
        })

    # Get first exercise
    skill_type, exercise_data = get_exercise_for_word(db, words[0], user_id)

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
        **auth,
    })


@router.get("/custom", response_class=HTMLResponse)
def start_custom_session(
    request: Request,
    search: Optional[str] = Query(None),
    filter: str = Query("all"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Start a custom learning session based on vocabulary filters."""
    # 1. Base Query (Search) - Fetch IDs ONLY for performance
    query = db.query(Word.id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Word.swedish.ilike(search_term)) | (Word.english.ilike(search_term))
        )
    
    # Get all candidate IDs (lightweight)
    all_candidate_ids = [r[0] for r in query.all()]
    
    # 2. Filter by Status (Python-side using IDs)
    filtered_ids = []
    
    if filter == "all":
        filtered_ids = all_candidate_ids
    else:
        # Fetch statuses efficiently
        from app.models import UserWordStatus, WordSkillMastery
        from app.services.mastery import PASS_THRESHOLD
        
        # Known overrides
        known_ids = {x[0] for x in db.query(UserWordStatus.word_id).filter(
            UserWordStatus.user_id == user_id, 
            UserWordStatus.status == 'already_known'
        ).all()}
        
        # Mastery scores
        masteries = db.query(WordSkillMastery).filter(WordSkillMastery.user_id == user_id).all()
        w_map = {}
        for m in masteries:
            if m.word_id not in w_map: w_map[m.word_id] = {}
            w_map[m.word_id][m.skill_type] = m.mastery_score
            
        for wid in all_candidate_ids:
            status = "not_started"
            if wid in known_ids:
                status = "already_known"
            elif wid in w_map:
                skills = w_map[wid]
                scores = [skills.get(s, 0.0) for s in ['read', 'listen', 'speak', 'write']]
                if all(s >= PASS_THRESHOLD for s in scores):
                    status = "mastered"
                elif all(s == 0 for s in scores):
                    status = "not_started"
                else:
                    status = "in_progress"
            
            if status == filter:
                filtered_ids.append(wid)

    if not filtered_ids:
        return templates.TemplateResponse("learning/no_words.html", {
            "request": request,
            "scenario": None, 
            "message": "No words match your current filters.",
            **auth,
        })
        
    # 3. Select Session Words (Top 10)
    import random
    random.shuffle(filtered_ids)
    selected_ids = filtered_ids[:10]

    # 4. Fetch full Word objects for the 10 selected IDs
    selected_words = db.query(Word).filter(Word.id.in_(selected_ids)).all()
    # DB doesn't preserve order from IN clause, shuffle for randomness
    random.shuffle(selected_words)
    
    # 5. Start Session
    skill_type, exercise_data = get_exercise_for_word(db, selected_words[0], user_id)
    word_ids = [w.id for w in selected_words]
    
    return templates.TemplateResponse("learning/session.html", {
        "request": request,
        "scenario": {"name": "Custom Practice", "icon": "🎯", "id": 0},
        "exercise": exercise_data,
        "skill_type": skill_type,
        "word_ids": word_ids,
        "current_index": 0,
        "total_words": len(selected_words),
        **auth,
    })


@router.get("/word/{word_id}", response_class=HTMLResponse)
def start_single_word_session(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Start a learning session for a specific single word."""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    # Get exercise
    skill_type, exercise_data = get_exercise_for_word(db, word, user_id)
    
    return templates.TemplateResponse("learning/session.html", {
        "request": request,
        "scenario": {"name": f"Word: {word.swedish}", "icon": "📖", "id": 0},
        "exercise": exercise_data,
        "skill_type": skill_type,
        "word_ids": [word.id],
        "current_index": 0,
        "total_words": 1,
        **auth,
    })


@router.get("/exercise/{word_id}", response_class=HTMLResponse)
def get_exercise(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
    word_ids: str = "",  # Comma-separated list of word IDs
    current_index: int = 0,
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Get exercise for a specific word."""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    skill_type, exercise_data = get_exercise_for_word(db, word, user_id)

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
        **auth,
    })


@router.post("/answer", response_model=AnswerResponse)
def submit_answer(
    answer_req: AnswerRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
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
        user_id,
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
    user_id: int = Depends(get_user_id),
    auth: dict = Depends(get_auth_context),
):
    """Show session completion summary."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()

    accuracy = (correct_count / words_practiced * 100) if words_practiced > 0 else 0

    # Record session completion in stats
    session_stats = record_session_completion(
        db=db,
        user_id=user_id,
        words_practiced=words_practiced,
        exercises_completed=words_practiced,  # One exercise per word
        time_seconds=time_seconds,
    )

    # Get updated scenario progress
    scenario_progress = get_scenario_progress(db, scenario_id, user_id)

    return templates.TemplateResponse("learning/complete.html", {
        "request": request,
        "scenario": scenario,
        "words_practiced": words_practiced,
        "correct_count": correct_count,
        "accuracy": round(accuracy),
        "time_seconds": time_seconds,
        "current_streak": session_stats["current_streak"],
        "scenario_progress": scenario_progress["progress_percent"],
        **auth,
    })
