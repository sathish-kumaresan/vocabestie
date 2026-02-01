from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class LearningSession(Base):
    """Tracks a learning session (40 or 50 exercises).

    Each session represents one learning flow:
    - 40 exercises: New words only (gate not met)
    - 50 exercises: 40 new word exercises + 10 review exercises (gate met)

    Gate conditions for 50 exercises:
    - mastered_word_count >= 10 AND
    - due_review_word_count >= 10

    Status:
    - 'active': Session in progress
    - 'completed': All exercises done or user finished
    """

    __tablename__ = "learning_session"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)

    # Session metadata
    total_exercises = Column(Integer, nullable=False)  # 40 or 50
    status = Column(String(20), default='active')  # 'active', 'completed'

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('ix_session_user_status', 'user_id', 'status'),
    )

    # Relationships
    user = relationship("User")
    scenario = relationship("Scenario")
    exercises = relationship("ExerciseQueue", back_populates="session", cascade="all, delete-orphan")
