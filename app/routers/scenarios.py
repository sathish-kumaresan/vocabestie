from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Scenario, Word
from app.schemas.scenario import ScenarioResponse, ScenarioListResponse
from app.schemas.word import WordResponse

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(db: Session = Depends(get_db)):
    """List all scenarios with word counts."""
    scenarios = db.query(Scenario).order_by(Scenario.display_order).all()

    scenario_responses = []
    for scenario in scenarios:
        scenario_responses.append(
            ScenarioResponse(
                id=scenario.id,
                name=scenario.name,
                slug=scenario.slug,
                icon=scenario.icon,
                description=scenario.description,
                category=scenario.category,
                difficulty_level=scenario.difficulty_level,
                word_count=scenario.word_count,
                display_order=scenario.display_order,
                created_at=scenario.created_at,
                progress_percent=0,  # TODO: Calculate from user mastery
            )
        )

    return ScenarioListResponse(scenarios=scenario_responses, total=len(scenario_responses))


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Get a single scenario by ID."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        slug=scenario.slug,
        icon=scenario.icon,
        description=scenario.description,
        category=scenario.category,
        difficulty_level=scenario.difficulty_level,
        word_count=scenario.word_count,
        display_order=scenario.display_order,
        created_at=scenario.created_at,
        progress_percent=0,
    )


@router.get("/{scenario_id}/words", response_model=List[WordResponse])
def get_scenario_words(scenario_id: int, db: Session = Depends(get_db)):
    """Get all words in a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    words = (
        db.query(Word)
        .filter(Word.scenario_id == scenario_id)
        .order_by(Word.display_order)
        .all()
    )

    return [
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
