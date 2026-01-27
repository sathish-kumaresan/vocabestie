from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Scenario, Word
from app.schemas.word import WordResponse, WordListResponse, WordDetailResponse
from app.services.stats import mark_word_as_known, unmark_word_as_known
from app.dependencies import get_user_id

router = APIRouter(prefix="/api/words", tags=["words"])


class MarkKnownRequest(BaseModel):
    known: bool


@router.post("/{word_id}/known")
def toggle_word_known(
    word_id: int,
    request: MarkKnownRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Mark or unmark a word as already known."""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    if request.known:
        mark_word_as_known(db, word_id, user_id)
        return {"success": True, "status": "already_known", "message": "Word marked as known"}
    else:
        unmark_word_as_known(db, word_id, user_id)
        return {"success": True, "status": "active", "message": "Word unmarked"}


@router.get("", response_model=WordListResponse)
def list_words(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search in Swedish or English"),
    scenario_id: Optional[int] = Query(None, description="Filter by scenario"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    limit: int = Query(50, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List words with optional filters."""
    query = db.query(Word)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Word.swedish.ilike(search_term)) | (Word.english.ilike(search_term))
        )

    if scenario_id:
        query = query.filter(Word.scenario_id == scenario_id)

    if difficulty:
        query = query.filter(Word.difficulty_level == difficulty)

    # Get total count
    total = query.count()

    # Apply pagination
    words = query.order_by(Word.id).offset(offset).limit(limit).all()

    word_responses = [
        WordResponse(
            id=word.id,
            swedish=word.swedish,
            english=word.english,
            grammar_hint=word.grammar_hint,
            example_sentence_sv=word.example_sentence_sv,
            example_sentence_en=word.example_sentence_en,
            difficulty_level=word.difficulty_level,
            scenario_id=word.scenario_id,
            display_order=word.display_order,
            created_at=word.created_at,
            status="not_started",
            mastery_percent=0,
        )
        for word in words
    ]

    return WordListResponse(words=word_responses, total=total)


@router.get("/{word_id}", response_model=WordDetailResponse)
def get_word(word_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a word."""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    # Get scenario info
    scenario_name = None
    scenario_icon = None
    if word.scenario_id:
        scenario = db.query(Scenario).filter(Scenario.id == word.scenario_id).first()
        if scenario:
            scenario_name = scenario.name
            scenario_icon = scenario.icon

    return WordDetailResponse(
        id=word.id,
        swedish=word.swedish,
        english=word.english,
        grammar_hint=word.grammar_hint,
        example_sentence_sv=word.example_sentence_sv,
        example_sentence_en=word.example_sentence_en,
        difficulty_level=word.difficulty_level,
        scenario_id=word.scenario_id,
        display_order=word.display_order,
        created_at=word.created_at,
        scenario_name=scenario_name,
        scenario_icon=scenario_icon,
        status="not_started",
        mastery_percent=0,
        skill_mastery={
            "read": 0.0,
            "listen": 0.0,
            "speak": 0.0,
            "write": 0.0,
        },
    )
