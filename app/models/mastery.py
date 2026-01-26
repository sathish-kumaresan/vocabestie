from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class WordSkillMastery(Base):
    """Tracks mastery of each skill (read/listen/speak/write) per word per user.

    mastery_score: 0.0 to 1.0, threshold 0.8 = passed
    skill_type: 'read', 'listen', 'speak', 'write'
    """

    __tablename__ = "word_skill_mastery"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    skill_type = Column(String(10), nullable=False)  # 'read', 'listen', 'speak', 'write'
    mastery_score = Column(Float, default=0.0)  # 0.0 to 1.0
    last_practiced = Column(DateTime, nullable=True)
    practice_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one record per user/word/skill combination
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', 'skill_type', name='uq_user_word_skill'),
    )

    # Relationships
    user = relationship("User")
    word = relationship("Word", back_populates="skill_masteries")


class UserWordStatus(Base):
    """Manual status override for words (e.g., marking as 'already_known').

    status: 'active' (default), 'already_known'
    """

    __tablename__ = "user_word_status"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    status = Column(String(20), default='active')  # 'active', 'already_known'
    marked_at = Column(DateTime, nullable=True)

    # Unique constraint: one status per user/word
    __table_args__ = (
        UniqueConstraint('user_id', 'word_id', name='uq_user_word_status'),
    )

    # Relationships
    user = relationship("User")
    word = relationship("Word", back_populates="user_statuses")


class UserStats(Base):
    """Aggregated user statistics for streaks and overall progress."""

    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_practice_date = Column(Date, nullable=True)
    total_practice_time_seconds = Column(Integer, default=0)
    total_words_mastered = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


class DailyPracticeLog(Base):
    """Daily practice activity log for streak and time tracking."""

    __tablename__ = "daily_practice_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    practice_date = Column(Date, nullable=False)
    practice_time_seconds = Column(Integer, default=0)
    words_practiced = Column(Integer, default=0)
    exercises_completed = Column(Integer, default=0)

    # Unique constraint: one log per user/date
    __table_args__ = (
        UniqueConstraint('user_id', 'practice_date', name='uq_user_practice_date'),
    )

    # Relationships
    user = relationship("User")
