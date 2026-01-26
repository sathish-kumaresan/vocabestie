from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Word(Base):
    """A Swedish vocabulary word belonging to a scenario."""

    __tablename__ = "words"

    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)
    swedish = Column(String(200), nullable=False)
    english = Column(String(200), nullable=False)
    example_sentence_sv = Column(Text, nullable=True)
    example_sentence_en = Column(Text, nullable=True)
    grammar_hint = Column(String(100), nullable=True)  # "en-word", "ett-word", "verb", etc.
    pronunciation_url = Column(String(500), nullable=True)
    difficulty_level = Column(String(5), nullable=True)  # A1, A2, B1, B2, C1, C2
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scenario = relationship("Scenario", back_populates="words")
    skill_masteries = relationship("WordSkillMastery", back_populates="word")
    user_statuses = relationship("UserWordStatus", back_populates="word")
