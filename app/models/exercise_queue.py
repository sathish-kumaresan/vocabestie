from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class ExerciseQueue(Base):
    """Individual exercise in a learning session queue.

    Queue ordering:
    - 0-39: New word exercises (10 words × 4 skills)
    - 40-49: Review exercises (10 mastered words × 1 skill each)

    IMPORTANT: Order ONLY by queue_order ASC, never by queue_type.
    The queue_type is for display/tracking purposes only.

    Status:
    - 'pending': Not yet attempted
    - 'completed': Exercise finished (correct or incorrect)
    - 'skipped': Skipped (e.g., word marked as known)
    """

    __tablename__ = "exercise_queue"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("learning_session.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    skill_type = Column(String(10), nullable=False)  # 'read', 'listen', 'speak', 'write'

    # Queue ordering
    queue_type = Column(String(10), nullable=False)  # 'new' or 'review' (for display only)
    queue_order = Column(Integer, nullable=False)  # 0-39 for new, 40-49 for review

    # Status tracking
    status = Column(String(20), default='pending')  # pending, completed, skipped
    completed_at = Column(DateTime, nullable=True)
    was_correct = Column(Boolean, nullable=True)  # True/False/None for pending

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('session_id', 'word_id', 'skill_type', name='uq_session_word_skill'),
        Index('ix_queue_session_order', 'session_id', 'queue_order'),
        Index('ix_queue_session_status', 'session_id', 'status'),
    )

    # Relationships
    session = relationship("LearningSession", back_populates="exercises")
    user = relationship("User")
    word = relationship("Word")
