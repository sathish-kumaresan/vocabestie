from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel


class WordCreate(BaseModel):
    term: str
    definition: str
    example: Optional[str] = None


class WordUpdate(BaseModel):
    term: Optional[str] = None
    definition: Optional[str] = None
    example: Optional[str] = None


class ReviewCardResponse(BaseModel):
    ease_factor: float
    interval: int
    repetitions: int
    next_review: date
    last_reviewed: Optional[datetime] = None

    class Config:
        from_attributes = True


class WordResponse(BaseModel):
    id: int
    term: str
    definition: str
    example: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    review_card: Optional[ReviewCardResponse] = None

    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    quality: int  # 0-5 rating for SM-2 algorithm


class QuizQuestion(BaseModel):
    word_id: int
    term: str
    options: List[str]
    quiz_type: str = "multiple_choice"


class QuizAnswer(BaseModel):
    word_id: int
    selected_answer: str
    quiz_type: str = "multiple_choice"


class QuizResult(BaseModel):
    word_id: int
    term: str
    correct: bool
    correct_answer: str
    selected_answer: str
