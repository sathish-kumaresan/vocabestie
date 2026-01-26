from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WordBase(BaseModel):
    swedish: str
    english: str
    grammar_hint: Optional[str] = None
    example_sentence_sv: Optional[str] = None
    example_sentence_en: Optional[str] = None
    difficulty_level: Optional[str] = None


class WordResponse(WordBase):
    id: int
    scenario_id: Optional[int] = None
    display_order: int
    created_at: Optional[datetime] = None
    # User-specific fields (computed)
    status: str = "not_started"  # not_started, in_progress, mastered, already_known
    mastery_percent: int = 0

    class Config:
        from_attributes = True


class WordListResponse(BaseModel):
    words: List[WordResponse]
    total: int


class WordDetailResponse(WordResponse):
    scenario_name: Optional[str] = None
    scenario_icon: Optional[str] = None
    # Skill mastery breakdown
    skill_mastery: dict = {
        "read": 0.0,
        "listen": 0.0,
        "speak": 0.0,
        "write": 0.0,
    }
