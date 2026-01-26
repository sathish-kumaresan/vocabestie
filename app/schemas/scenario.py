from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ScenarioBase(BaseModel):
    name: str
    slug: str
    icon: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty_level: Optional[str] = None


class ScenarioResponse(ScenarioBase):
    id: int
    word_count: int
    display_order: int
    created_at: Optional[datetime] = None
    progress_percent: int = 0  # Computed field for user progress

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    scenarios: List[ScenarioResponse]
    total: int
