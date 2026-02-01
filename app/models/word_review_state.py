from datetime import datetime, date
from sqlalchemy import Column, Integer, Float, DateTime, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class WordReviewState(Base):
    """SM2 spaced repetition state per word (NOT per skill).

    This tracks the spaced repetition scheduling for each word the user
    has mastered. When a word reaches mastery (>=80% on all 4 skills),
    it enters the SM2 review system.

    Fields:
    - easiness_factor: SM2 EF (default 2.5, min 1.3)
    - sm2_interval: Days until next review
    - sm2_repetitions: Successful review count
    - next_review_date: When word is due for review
    - consecutive_failures: Track failures for mastery demotion
    """

    __tablename__ = "word_review_state"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)

    # SM2 algorithm fields
    easiness_factor = Column(Float, default=2.5)  # EF, min 1.3
    sm2_interval = Column(Integer, default=0)  # Days until next review
    sm2_repetitions = Column(Integer, default=0)  # Successful repetition count
    next_review_date = Column(Date, nullable=True)  # When due for review

    # Failure tracking for mastery demotion
    consecutive_failures = Column(Integer, default=0)  # Reset on correct answer

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one review state per user/word
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', name='uq_user_word_review'),
        Index('ix_word_review_user_date', 'user_id', 'next_review_date'),
    )

    # Relationships
    user = relationship("User")
    word = relationship("Word")
